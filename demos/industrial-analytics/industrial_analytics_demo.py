#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from industrial_analytics_dataset import (
    CDC_CHANGES_SQL,
    DEFAULT_SCHEMA,
    DEFAULT_SEARCH_TERM,
    PsqlClient,
    PsqlConfig,
    TABLE_COLUMNS,
    load_environment,
    validate_identifier,
)

ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_STATE_FILE = ".tmp/industrial-analytics-demo-state.json"
DEFAULT_WORKER_IDS = (
    "industrial-sales-worker,"
    "industrial-production-worker,"
    "industrial-quality-worker"
)
DEFAULT_TIMEOUT_SECONDS = 420
RETRY_DELAY_SECONDS = 5
PROGRESS_REPORT_INTERVAL_SECONDS = 30
PROGRESS_TABLE_LIMIT = 5
TOPIC_PREFIX = "cdc_sync"
SOURCE_CONNECTION_NAME = "Demo industrial analytics PostgreSQL local"
DESTINATION_NAME = "Demo industrial analytics ClickHouse local"
SYNC_CONFIG_NAME_PREFIX = "Demo industrial analytics"


class AnalyticsDemoError(RuntimeError):
    pass


@dataclass(frozen=True)
class IndustrialColumnSpec:
    name: str
    clickhouse_type: str
    nullable: bool = False


@dataclass(frozen=True)
class IndustrialTableSpec:
    name: str
    columns: tuple[IndustrialColumnSpec, ...]
    primary_key: tuple[str, ...] = ("id",)

    def cdc_topic(self, schema_name: str) -> str:
        return f"{TOPIC_PREFIX}.{schema_name}.{self.name}"


@dataclass(frozen=True)
class IndustrialWorkerModuleSpec:
    worker_id: str
    name: str
    description: str
    tables: tuple[IndustrialTableSpec, ...]


@dataclass(frozen=True)
class EngineBenchmarkResult:
    engine: str
    phase: str
    query_name: str
    elapsed_ms: float
    row_count: int
    signature: str


@dataclass(frozen=True)
class QuerySignature:
    name: str
    row_count: int
    signature: str


@dataclass(frozen=True)
class TableSyncProgress:
    table_name: str
    postgres_rows: int
    clickhouse_rows: int

    @property
    def delta_rows(self) -> int:
        return self.postgres_rows - self.clickhouse_rows


@dataclass(frozen=True)
class AnalyticsBenchmarkQuery:
    name: str
    postgres_sql: str
    clickhouse_ctes: tuple[str, ...]
    clickhouse_select: str


class ApiClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def request_json(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> Any:
        data = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request = Request(
            f"{self.base_url}{path}",
            data=data,
            headers=headers,
            method=method,
        )
        try:
            with urlopen(request, timeout=15) as response:
                body = response.read().decode("utf-8")
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise AnalyticsDemoError(
                f"La API respondió {exc.code} en {method} {path}: {body}"
            ) from exc
        except URLError as exc:
            raise AnalyticsDemoError(
                f"No se pudo conectar con la API en {self.base_url}"
            ) from exc

        if not body:
            return None

        return json.loads(body)


class IndustrialAnalyticsDemoRunner:
    def __init__(self, args: argparse.Namespace) -> None:
        self.env = _load_environment()
        self.schema_name = validate_identifier(args.schema)
        self.worker_ids = _parse_worker_ids(args.worker_ids)
        self.search_term = args.term
        self.clickhouse_database = validate_identifier(args.clickhouse_database)
        self.state_file = ROOT_DIR / args.state_file
        self.api_client = ApiClient(
            self.env.get("DEMO_API_BASE_URL")
            or f"http://localhost:{self.env.get('API_PORT', '8000')}"
        )
        self.connect_base_url = (
            f"http://localhost:{self.env.get('CONNECT_PORT', '8083')}"
        )
        self.psql_client = PsqlClient(
            PsqlConfig(
                service="postgres",
                database=self.env.get("POSTGRES_DB", "cdc_sync"),
                user=self.env.get("POSTGRES_USER", "cdc_sync"),
            )
        )
        self.table_specs_by_name = build_industrial_table_specs_by_name()
        self.modules_by_worker_id = build_industrial_worker_modules(
            self.table_specs_by_name
        )
        self.selected_modules = self._selected_modules()
        self.table_specs = tuple(
            table
            for module in self.selected_modules
            for table in module.tables
        )
        self.benchmark_queries = build_benchmark_queries(
            schema_name=self.schema_name,
            clickhouse_database=self.clickhouse_database,
            search_term=self.search_term,
        )

    def configure(self) -> None:
        _print_step("Creando configuración CDC industrial desde la API")
        self._wait_for_api()
        source_connection = self._upsert_source_connection()
        destination = self._upsert_destination()
        workers_by_identifier = self._list_by_key("/api/v1/workers", "worker_id")

        worker_state: dict[str, dict[str, Any]] = {}
        for module in self.selected_modules:
            worker = self._upsert_worker(
                module=module,
                existing_worker=workers_by_identifier.get(module.worker_id),
            )
            sync_config = self._upsert_sync_config(
                module=module,
                source_connection_id=source_connection["id"],
                destination_id=destination["id"],
            )
            assignment = self.api_client.request_json(
                "PUT",
                f"/api/v1/workers/{worker['id']}/config-assignment",
                {"config_id": sync_config["id"]},
            )
            runtime_config = self.api_client.request_json(
                "GET",
                f"/workers/{module.worker_id}/config",
            )
            self._assert_runtime_config(runtime_config, module)
            worker_state[module.worker_id] = {
                "id": worker["id"],
                "config_id": sync_config["id"],
                "assignment": assignment,
                "container_name": _container_name(module.worker_id),
                "tables": [table.name for table in module.tables],
            }

        self._save_state(
            {
                **self._load_state(),
                "schema_name": self.schema_name,
                "worker_ids": self.worker_ids,
                "workers": worker_state,
                "source_connection_id": source_connection["id"],
                "destination_id": destination["id"],
            }
        )
        _print_ok("Configuración CDC industrial lista para materializar")

    def materialize(self) -> None:
        state = self._require_state("source_connection_id")
        _print_step("Materializando conector Debezium industrial desde la API")
        self._wait_for_api()
        self._wait_for_connect()
        materialized = self.api_client.request_json(
            "PUT",
            f"/api/v1/source-connections/{state['source_connection_id']}/cdc-connector",
        )
        self._assert_captured_tables(materialized)
        connector_name = materialized["connector_name"]
        state["connector_name"] = connector_name
        state["captured_tables"] = list(materialized["captured_tables"])
        self._save_state(state)
        self._wait_for_connector(connector_name)
        _print_ok(f"Conector Debezium listo: {connector_name}")

    def wait_snapshot(self) -> None:
        _print_step("Esperando convergencia del snapshot inicial")
        signatures = self._wait_for_convergence(
            label="snapshot inicial",
            initial_signatures=None,
            require_changed=False,
        )
        state = self._load_state()
        state["initial_signatures"] = _signature_state(signatures)
        self._save_state(state)
        _print_signature_summary("snapshot inicial", signatures)
        _print_ok("Snapshot inicial reconciliado")

    def benchmark(self) -> None:
        self._run_benchmark_phase(
            phase="inicial",
            require_changed=False,
        )

    def changes(self) -> None:
        _print_step("Aplicando inserts, updates y deletes CDC industriales")
        output = self.psql_client.report_sql_file(
            CDC_CHANGES_SQL,
            {"schema_name": self.schema_name},
        )
        for raw_line in output.splitlines():
            line = raw_line.strip()
            if line:
                print(f"[analytics-demo]   {line}", flush=True)

        _print_ok("Cambios CDC industriales aplicados en PostgreSQL")

    def wait_cdc(self) -> None:
        state = self._require_state("initial_signatures")
        initial_signatures = _load_signature_state(state["initial_signatures"])
        _print_step("Esperando convergencia tras cambios CDC")
        signatures = self._wait_for_convergence(
            label="cambios CDC",
            initial_signatures=initial_signatures,
            require_changed=True,
        )
        state["after_signatures"] = _signature_state(signatures)
        self._save_state(state)
        _print_signature_summary("cambios CDC", signatures)
        _print_ok("PostgreSQL y ClickHouse vuelven a coincidir")

    def benchmark_after(self) -> None:
        self._run_benchmark_phase(
            phase="cdc",
            require_changed=True,
        )

    def reset(self) -> None:
        _print_step("Reiniciando estado local de la demo industrial")
        for worker_id in self.worker_ids:
            _run(["docker", "rm", "-f", _container_name(worker_id)], check=False)
        _run(
            ["docker", "compose", "down", "-v", "--remove-orphans"],
            check=False,
            timeout_seconds=180,
        )
        if self.state_file.exists():
            self.state_file.unlink()

        _print_ok("Estado local eliminado")

    def _run_benchmark_phase(self, *, phase: str, require_changed: bool) -> None:
        state = self._load_state()
        initial_signatures = _load_optional_initial_signatures(state)
        _print_step(f"Barrera de convergencia antes del benchmark {phase}")
        self._wait_for_convergence(
            label=f"benchmark {phase}",
            initial_signatures=initial_signatures,
            require_changed=require_changed,
        )
        _print_step(f"Benchmark {phase}: PostgreSQL frente a ClickHouse")
        results: list[EngineBenchmarkResult] = []
        for query in self.benchmark_queries:
            postgres_result = self._postgres_benchmark_result(query, phase)
            clickhouse_result = self._clickhouse_benchmark_result(query, phase)
            self._assert_engine_results_match(postgres_result, clickhouse_result)
            results.extend([postgres_result, clickhouse_result])
            _print_benchmark_result(postgres_result)
            _print_benchmark_result(clickhouse_result)

        _print_speedup_summary(results)

    def _wait_for_convergence(
        self,
        *,
        label: str,
        initial_signatures: dict[str, QuerySignature] | None,
        require_changed: bool,
    ) -> list[QuerySignature]:
        self._wait_for_postgres()
        self._assert_runtime_health()
        self._wait_for_clickhouse()
        postgres_signatures = self._postgres_signatures()
        _assert_signatures_changed(
            postgres_signatures,
            initial_signatures,
            require_changed=require_changed,
        )
        expected_table_counts = self._postgres_table_counts()
        started_at = time.monotonic()
        deadline = started_at + int(
            self.env.get(
                "ANALYTICS_DEMO_TIMEOUT_SECONDS",
                DEFAULT_TIMEOUT_SECONDS,
            )
        )
        next_progress_report_at = started_at
        last_error: Exception | None = None
        while time.monotonic() <= deadline:
            self._assert_runtime_health()
            current_progress_rows: list[TableSyncProgress] | None = None
            try:
                actual_table_counts = self._clickhouse_live_table_counts()
                current_progress_rows = _table_progress_rows(
                    expected_table_counts,
                    actual_table_counts,
                )
                _assert_table_counts_match(current_progress_rows)
                clickhouse_signatures = self._clickhouse_signatures()
                _assert_signature_sets_match(postgres_signatures, clickhouse_signatures)
                return postgres_signatures
            except (AnalyticsDemoError, subprocess.CalledProcessError) as exc:
                last_error = exc
                self._assert_runtime_health()
                current_time = time.monotonic()
                if current_time >= next_progress_report_at:
                    self._print_convergence_progress(
                        label=label,
                        started_at=started_at,
                        expected_table_counts=expected_table_counts,
                        current_progress_rows=current_progress_rows,
                        last_error=last_error,
                    )
                    next_progress_report_at = (
                        current_time + PROGRESS_REPORT_INTERVAL_SECONDS
                    )

                sleep_seconds = min(RETRY_DELAY_SECONDS, deadline - time.monotonic())
                if sleep_seconds <= 0:
                    break

                time.sleep(sleep_seconds)

        raise AnalyticsDemoError(
            f"ClickHouse no convergió para {label} antes del timeout. "
            f"Último error: {last_error}"
        )

    def _selected_modules(self) -> tuple[IndustrialWorkerModuleSpec, ...]:
        unsupported_worker_ids = [
            worker_id
            for worker_id in self.worker_ids
            if worker_id not in self.modules_by_worker_id
        ]
        if unsupported_worker_ids:
            supported = ", ".join(self.modules_by_worker_id)
            unsupported = ", ".join(unsupported_worker_ids)
            raise AnalyticsDemoError(
                f"Workers industriales no soportados: {unsupported}. "
                f"Valores válidos: {supported}"
            )

        return tuple(
            self.modules_by_worker_id[worker_id]
            for worker_id in self.worker_ids
        )

    def _postgres_signatures(self) -> list[QuerySignature]:
        return [
            self._postgres_query_signature(query)
            for query in self.benchmark_queries
        ]

    def _clickhouse_signatures(self) -> list[QuerySignature]:
        return [
            self._clickhouse_query_signature(query)
            for query in self.benchmark_queries
        ]

    def _postgres_table_counts(self) -> dict[str, int]:
        schema_name = _quote_postgres_identifier(self.schema_name)
        counts_sql = _postgres_table_counts_sql(schema_name, self.table_specs)
        return _parse_table_count_rows(self.psql_client.query(counts_sql, {}))

    def _clickhouse_live_table_counts(self) -> dict[str, int]:
        counts_sql = _clickhouse_live_table_counts_sql(
            self.clickhouse_database,
            self.table_specs,
        )
        return _parse_table_count_rows(self._clickhouse_query(counts_sql))

    def _print_convergence_progress(
        self,
        *,
        label: str,
        started_at: float,
        expected_table_counts: dict[str, int],
        current_progress_rows: list[TableSyncProgress] | None,
        last_error: Exception | None,
    ) -> None:
        elapsed_seconds = int(time.monotonic() - started_at)
        if current_progress_rows is not None:
            _print_convergence_progress(
                label=label,
                elapsed_seconds=elapsed_seconds,
                progress_rows=current_progress_rows,
                last_error=last_error,
            )
            return

        try:
            actual_table_counts = self._clickhouse_live_table_counts()
        except AnalyticsDemoError as exc:
            _print_convergence_progress_unavailable(
                label=label,
                elapsed_seconds=elapsed_seconds,
                progress_error=exc,
                last_error=last_error,
            )
            return

        progress_rows = _table_progress_rows(
            expected_table_counts,
            actual_table_counts,
        )
        _print_convergence_progress(
            label=label,
            elapsed_seconds=elapsed_seconds,
            progress_rows=progress_rows,
            last_error=last_error,
        )

    def _postgres_benchmark_result(
        self,
        query: AnalyticsBenchmarkQuery,
        phase: str,
    ) -> EngineBenchmarkResult:
        started_at = time.perf_counter()
        signature = self._postgres_query_signature(query)
        elapsed_ms = (time.perf_counter() - started_at) * 1000
        return EngineBenchmarkResult(
            engine="PostgreSQL",
            phase=phase,
            query_name=query.name,
            elapsed_ms=elapsed_ms,
            row_count=signature.row_count,
            signature=signature.signature,
        )

    def _clickhouse_benchmark_result(
        self,
        query: AnalyticsBenchmarkQuery,
        phase: str,
    ) -> EngineBenchmarkResult:
        started_at = time.perf_counter()
        signature = self._clickhouse_query_signature(query)
        elapsed_ms = (time.perf_counter() - started_at) * 1000
        return EngineBenchmarkResult(
            engine="ClickHouse",
            phase=phase,
            query_name=query.name,
            elapsed_ms=elapsed_ms,
            row_count=signature.row_count,
            signature=signature.signature,
        )

    def _postgres_query_signature(
        self,
        query: AnalyticsBenchmarkQuery,
    ) -> QuerySignature:
        sql = _postgres_signature_sql(query.postgres_sql)
        output = self.psql_client.query(sql, {})
        row_count, signature = _parse_signature_output(output, query.name)
        return QuerySignature(query.name, row_count, signature)

    def _clickhouse_query_signature(
        self,
        query: AnalyticsBenchmarkQuery,
    ) -> QuerySignature:
        sql = _clickhouse_signature_sql(query, self.clickhouse_database)
        output = self._clickhouse_query(sql)
        row_count, signature = _parse_signature_output(output, query.name)
        return QuerySignature(query.name, row_count, signature)

    def _assert_engine_results_match(
        self,
        postgres_result: EngineBenchmarkResult,
        clickhouse_result: EngineBenchmarkResult,
    ) -> None:
        if postgres_result.row_count != clickhouse_result.row_count:
            raise AnalyticsDemoError(
                f"{postgres_result.query_name}: filas distintas entre motores "
                f"({postgres_result.row_count} != {clickhouse_result.row_count})"
            )

        if postgres_result.signature == clickhouse_result.signature:
            return

        raise AnalyticsDemoError(
            f"{postgres_result.query_name}: firma distinta entre motores "
            f"({postgres_result.signature} != {clickhouse_result.signature})"
        )

    def _upsert_source_connection(self) -> dict[str, Any]:
        payload = {
            "name": SOURCE_CONNECTION_NAME,
            "source_type": "postgresql",
            "host": "postgres",
            "port": 5432,
            "database_name": self.env.get("POSTGRES_DB", "cdc_sync"),
            "credentials": {
                "user": self.env.get("POSTGRES_USER", "cdc_sync"),
                "password": self.env.get("POSTGRES_PASSWORD", "cdc_sync"),
            },
        }
        existing = self._find_by_name("/api/v1/source-connections", SOURCE_CONNECTION_NAME)
        if existing is None:
            return self.api_client.request_json("POST", "/api/v1/source-connections", payload)

        return self.api_client.request_json(
            "PUT",
            f"/api/v1/source-connections/{existing['id']}",
            payload,
        )

    def _upsert_destination(self) -> dict[str, Any]:
        payload = {
            "name": DESTINATION_NAME,
            "destination_type": "clickhouse",
            "host": "clickhouse",
            "port": 9000,
            "secure": False,
            "database_name": self.clickhouse_database,
            "credentials": {
                "user": self.env.get("CLICKHOUSE_USER", "cdc_sync"),
                "password": self.env.get("CLICKHOUSE_PASSWORD", "cdc_sync"),
            },
        }
        existing = self._find_by_name("/api/v1/destinations", DESTINATION_NAME)
        if existing is None:
            return self.api_client.request_json("POST", "/api/v1/destinations", payload)

        return self.api_client.request_json(
            "PUT",
            f"/api/v1/destinations/{existing['id']}",
            payload,
        )

    def _upsert_worker(
        self,
        *,
        module: IndustrialWorkerModuleSpec,
        existing_worker: dict[str, Any] | None,
    ) -> dict[str, Any]:
        payload = {
            "worker_id": module.worker_id,
            "name": module.name,
            "description": module.description,
            "kafka_group_id": f"cdc-sync-demo-{module.worker_id}",
            "enabled": True,
        }
        if existing_worker is None:
            return self.api_client.request_json("POST", "/api/v1/workers", payload)

        return self.api_client.request_json(
            "PUT",
            f"/api/v1/workers/{existing_worker['id']}",
            payload,
        )

    def _upsert_sync_config(
        self,
        *,
        module: IndustrialWorkerModuleSpec,
        source_connection_id: str,
        destination_id: str,
    ) -> dict[str, Any]:
        payload = {
            "name": _sync_config_name(module),
            "source_connection_id": source_connection_id,
            "destination_id": destination_id,
            "sync_mode": "realtime",
            "tables": [
                self._table_payload(table)
                for table in module.tables
            ],
            "enabled": True,
        }
        existing = self._find_by_name("/api/v1/configs", _sync_config_name(module))
        if existing is None:
            return self.api_client.request_json("POST", "/api/v1/configs", payload)

        return self.api_client.request_json(
            "PUT",
            f"/api/v1/configs/{existing['id']}",
            payload,
        )

    def _table_payload(self, table: IndustrialTableSpec) -> dict[str, Any]:
        return {
            "logical_name": table.name,
            "source_schema": self.schema_name,
            "source_table": table.name,
            "cdc_topic": table.cdc_topic(self.schema_name),
            "destination_table": table.name,
            "primary_key_fields": table.primary_key,
            "destination_columns": [
                {
                    "name": column.name,
                    "destination_type": column.clickhouse_type,
                    "nullable": column.nullable,
                }
                for column in table.columns
            ],
            "enabled": True,
        }

    def _assert_runtime_config(
        self,
        runtime_config: Any,
        module: IndustrialWorkerModuleSpec,
    ) -> None:
        if not isinstance(runtime_config, dict):
            raise AnalyticsDemoError("El contrato runtime debe ser un objeto JSON")

        worker_payload = runtime_config.get("worker")
        if not isinstance(worker_payload, dict):
            raise AnalyticsDemoError("El contrato runtime no incluye worker")

        if worker_payload.get("worker_id") != module.worker_id:
            raise AnalyticsDemoError("El contrato runtime no pertenece al worker industrial")

        tables_payload = runtime_config.get("tables")
        if not isinstance(tables_payload, dict):
            raise AnalyticsDemoError("El contrato runtime no incluye tablas")

        expected_tables = {table.name for table in module.tables}
        missing_tables = sorted(expected_tables - set(tables_payload))
        if not missing_tables:
            return

        raise AnalyticsDemoError(
            "El contrato runtime no incluye todas las tablas industriales: "
            + ", ".join(missing_tables)
        )

    def _assert_runtime_health(self) -> None:
        self._assert_compose_service_running("clickhouse")
        for worker_id in self._worker_ids_from_state_or_args():
            self._assert_container_running(_container_name(worker_id), f"worker {worker_id}")

        self._assert_connector_running(self._connector_name_from_state())

    def _assert_compose_service_running(self, service_name: str) -> None:
        container_id = _run(
            ["docker", "compose", "ps", "-a", "-q", service_name],
            check=False,
        ).strip()
        if container_id:
            self._assert_container_running(container_id, service_name)
            return

        raise AnalyticsDemoError(
            f"El servicio Docker '{service_name}' no tiene contenedor asociado"
        )

    def _assert_container_running(self, container_name: str, label: str) -> None:
        output = _run(
            [
                "docker",
                "inspect",
                "-f",
                "{{.State.Status}}|{{.State.OOMKilled}}|{{.State.ExitCode}}|{{.State.Error}}",
                container_name,
            ],
            check=False,
        ).strip()
        if "No such object" in output or "no such object" in output:
            raise AnalyticsDemoError(f"El contenedor de {label} no existe")

        status, oom_killed, exit_code, error = _split_container_state(output, label)
        if status == "running":
            return

        detail = f"estado={status}; exit_code={exit_code}; oom_killed={oom_killed}"
        if error:
            detail = f"{detail}; error={error}"

        raise AnalyticsDemoError(f"El contenedor de {label} no sigue running: {detail}")

    def _assert_connector_running(self, connector_name: str) -> None:
        status = _http_get(f"{self.connect_base_url}/connectors/{connector_name}/status")
        connector = status.get("connector", {})
        tasks = status.get("tasks", [])
        connector_running = connector.get("state") == "RUNNING"
        tasks_running = bool(tasks) and all(
            task.get("state") == "RUNNING"
            for task in tasks
        )
        if connector_running and tasks_running:
            return

        raise AnalyticsDemoError(
            "El conector Debezium no sigue RUNNING: "
            + json.dumps(status, ensure_ascii=False, sort_keys=True)
        )

    def _worker_ids_from_state_or_args(self) -> list[str]:
        state = self._load_state()
        raw_worker_ids = state.get("worker_ids")
        if isinstance(raw_worker_ids, list):
            return _validate_worker_ids(
                [str(worker_id) for worker_id in raw_worker_ids],
                "worker_ids del estado",
            )

        return self.worker_ids

    def _connector_name_from_state(self) -> str:
        state = self._require_state("source_connection_id")
        connector_name = state.get("connector_name")
        if isinstance(connector_name, str) and connector_name:
            return connector_name

        return f"cdc-sync-postgresql-{state['source_connection_id']}"

    def _assert_captured_tables(self, materialized: Any) -> None:
        if not isinstance(materialized, dict):
            raise AnalyticsDemoError("La materialización CDC no devolvió un objeto JSON")

        captured_tables = materialized.get("captured_tables")
        if not isinstance(captured_tables, list):
            raise AnalyticsDemoError("La materialización CDC no devolvió captured_tables")

        expected_tables = {
            f"{self.schema_name}.{table.name}"
            for table in self.table_specs
        }
        missing_tables = sorted(expected_tables - set(captured_tables))
        if not missing_tables:
            return

        raise AnalyticsDemoError(
            "El conector Debezium no captura todas las tablas industriales: "
            + ", ".join(missing_tables)
        )

    def _find_by_name(self, path: str, name: str) -> dict[str, Any] | None:
        for item in self.api_client.request_json("GET", path):
            if item.get("name") == name:
                return item

        return None

    def _list_by_key(self, path: str, key: str) -> dict[str, dict[str, Any]]:
        items = self.api_client.request_json("GET", path)
        return {str(item[key]): item for item in items}

    def _load_state(self) -> dict[str, Any]:
        if not self.state_file.exists():
            return {}

        with self.state_file.open("r", encoding="utf-8") as state_reader:
            loaded_state = json.load(state_reader)

        if isinstance(loaded_state, dict):
            return loaded_state

        raise AnalyticsDemoError(f"El estado {self.state_file} debe ser un objeto JSON")

    def _require_state(self, *required_keys: str) -> dict[str, Any]:
        state = self._load_state()
        missing_keys = [key for key in required_keys if key not in state]
        if not missing_keys:
            return state

        raise AnalyticsDemoError(
            "Falta estado de demo industrial: " + ", ".join(missing_keys)
        )

    def _save_state(self, state: dict[str, Any]) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        with self.state_file.open("w", encoding="utf-8") as state_writer:
            json.dump(state, state_writer, indent=2, sort_keys=True)
            state_writer.write("\n")

    def _wait_for_api(self) -> None:
        _wait_until(
            "API REST",
            lambda: self.api_client.request_json("GET", "/health") is not None,
        )

    def _wait_for_connect(self) -> None:
        _wait_until(
            "Kafka Connect",
            lambda: _http_get(f"{self.connect_base_url}/") is not None,
        )

    def _wait_for_connector(self, connector_name: str) -> None:
        def connector_is_running() -> bool:
            status = _http_get(f"{self.connect_base_url}/connectors/{connector_name}/status")
            connector = status.get("connector", {})
            tasks = status.get("tasks", [])
            return (
                connector.get("state") == "RUNNING"
                and bool(tasks)
                and all(task.get("state") == "RUNNING" for task in tasks)
            )

        _wait_until(f"conector {connector_name}", connector_is_running, attempts=30)

    def _wait_for_postgres(self) -> None:
        _wait_until(
            "PostgreSQL OLTP",
            lambda: self.psql_client.query("SELECT 1;", {}).strip() == "1",
        )

    def _wait_for_clickhouse(self) -> None:
        _wait_until(
            "ClickHouse",
            lambda: self._clickhouse_query("SELECT 1").strip() == "1",
        )

    def _clickhouse_query(self, query: str) -> str:
        command = [
            "docker",
            "compose",
            "exec",
            "-T",
            "clickhouse",
            "clickhouse-client",
            "--user",
            self.env.get("CLICKHOUSE_USER", "cdc_sync"),
            f"--password={self.env.get('CLICKHOUSE_PASSWORD', 'cdc_sync')}",
            "--query",
            query,
        ]
        return _run(command)


def build_industrial_table_specs_by_name() -> dict[str, IndustrialTableSpec]:
    return {
        table_name: IndustrialTableSpec(
            name=table_name,
            columns=tuple(
                IndustrialColumnSpec(
                    name=column_name,
                    clickhouse_type=clickhouse_type_for_column(column_name),
                )
                for column_name in column_names
            ),
        )
        for table_name, column_names in TABLE_COLUMNS.items()
    }


def build_industrial_worker_modules(
    table_specs_by_name: dict[str, IndustrialTableSpec],
) -> dict[str, IndustrialWorkerModuleSpec]:
    modules = (
        IndustrialWorkerModuleSpec(
            worker_id="industrial-sales-worker",
            name="Demo industrial ventas",
            description="Sincroniza clientes, productos, pedidos y líneas de pedido.",
            tables=_tables_for_module(
                table_specs_by_name,
                ("clientes", "productos", "pedidos", "lineas_pedido"),
            ),
        ),
        IndustrialWorkerModuleSpec(
            worker_id="industrial-production-worker",
            name="Demo industrial producción",
            description="Sincroniza máquinas, órdenes de producción y sensores.",
            tables=_tables_for_module(
                table_specs_by_name,
                ("maquinas", "ordenes_produccion", "lecturas_sensores"),
            ),
        ),
        IndustrialWorkerModuleSpec(
            worker_id="industrial-quality-worker",
            name="Demo industrial calidad",
            description="Sincroniza proveedores, materiales, lotes, consumos y calidad.",
            tables=_tables_for_module(
                table_specs_by_name,
                (
                    "proveedores",
                    "materiales",
                    "lotes_material",
                    "consumos_material",
                    "no_conformidades",
                ),
            ),
        ),
    )
    return {module.worker_id: module for module in modules}


def _tables_for_module(
    table_specs_by_name: dict[str, IndustrialTableSpec],
    table_names: tuple[str, ...],
) -> tuple[IndustrialTableSpec, ...]:
    return tuple(table_specs_by_name[table_name] for table_name in table_names)


def clickhouse_type_for_column(column_name: str) -> str:
    if column_name == "id" or column_name.endswith("_id"):
        return "UInt64"

    if column_name in {"activo", "fuera_rango", "numero_linea", "severidad"}:
        return "UInt8"

    if column_name == "created_at" or column_name.startswith("fecha_"):
        return "DateTime64(3, 'UTC')"

    decimal_type = _decimal_type_for_column(column_name)
    if decimal_type is not None:
        return decimal_type

    return "String"


def _decimal_type_for_column(column_name: str) -> str | None:
    decimal_10_2_columns = {
        "precio_base",
        "coste_unitario",
        "precio_unitario",
        "temperatura",
        "vibracion",
        "consumo_kw",
    }
    if column_name in decimal_10_2_columns:
        return "Decimal(10, 2)"

    decimal_12_2_columns = {
        "importe_total",
        "cantidad",
        "cantidad_planificada",
        "cantidad_real",
        "cantidad_recibida",
        "cantidad_consumida",
        "coste_total",
        "coste_consumido",
        "coste_estimado",
    }
    if column_name in decimal_12_2_columns:
        return "Decimal(12, 2)"

    return None


def build_benchmark_queries(
    *,
    schema_name: str,
    clickhouse_database: str,
    search_term: str,
) -> tuple[AnalyticsBenchmarkQuery, ...]:
    pg_schema = _quote_postgres_identifier(schema_name)
    term_literal = _sql_literal(search_term)
    return (
        _monthly_revenue_query(pg_schema),
        _text_search_query(pg_schema, term_literal),
        _sensor_activity_query(pg_schema),
        _client_activity_query(pg_schema),
        _quality_traceability_query(pg_schema),
    )


def _monthly_revenue_query(pg_schema: str) -> AnalyticsBenchmarkQuery:
    postgres_sql = f"""
WITH base_facturacion AS (
    SELECT
        date_trunc('month', p.fecha_pedido) AS mes,
        pr.familia,
        c.id AS cliente_id,
        p.id AS pedido_id,
        lp.cantidad * lp.precio_unitario AS importe_linea,
        lp.cantidad * (lp.precio_unitario - lp.coste_unitario) AS margen_linea
    FROM {pg_schema}.pedidos p
    JOIN {pg_schema}.clientes c ON c.id = p.cliente_id
    JOIN {pg_schema}.lineas_pedido lp ON lp.pedido_id = p.id
    JOIN {pg_schema}.productos pr ON pr.id = lp.producto_id
),
facturacion_mensual AS (
    SELECT
        mes,
        familia,
        COUNT(DISTINCT cliente_id) AS clientes_distintos,
        COUNT(DISTINCT pedido_id) AS pedidos_distintos,
        SUM(importe_linea) AS facturacion,
        SUM(margen_linea) AS margen
    FROM base_facturacion
    GROUP BY mes, familia
)
SELECT concat_ws(
    '|',
    to_char(mes AT TIME ZONE 'UTC', 'YYYY-MM-DD'),
    familia,
    clientes_distintos::TEXT,
    pedidos_distintos::TEXT,
    FLOOR(facturacion * 100)::TEXT,
    FLOOR(margen * 100)::TEXT
) AS row_signature
FROM facturacion_mensual
"""
    clickhouse_ctes = (
        """
base_facturacion AS (
    SELECT
        toStartOfMonth(p.fecha_pedido) AS mes,
        pr.familia AS familia,
        c.id AS cliente_id,
        p.id AS pedido_id,
        lp.cantidad * lp.precio_unitario AS importe_linea,
        lp.cantidad * (lp.precio_unitario - lp.coste_unitario) AS margen_linea
    FROM pedidos AS p
    INNER JOIN clientes AS c ON c.id = p.cliente_id
    INNER JOIN lineas_pedido AS lp ON lp.pedido_id = p.id
    INNER JOIN productos AS pr ON pr.id = lp.producto_id
)""",
        """
facturacion_mensual AS (
    SELECT
        mes,
        familia,
        uniqExact(cliente_id) AS clientes_distintos,
        uniqExact(pedido_id) AS pedidos_distintos,
        sum(importe_linea) AS facturacion,
        sum(margen_linea) AS margen
    FROM base_facturacion
    GROUP BY mes, familia
)""",
    )
    clickhouse_select = """
SELECT concat(
    toString(toDate(mes)),
    '|', familia,
    '|', toString(clientes_distintos),
    '|', toString(pedidos_distintos),
    '|', toString(toInt64(floor(facturacion * 100))),
    '|', toString(toInt64(floor(margen * 100)))
) AS row_signature
FROM facturacion_mensual
"""
    return AnalyticsBenchmarkQuery(
        name="01_evolucion_mensual_facturacion",
        postgres_sql=postgres_sql,
        clickhouse_ctes=clickhouse_ctes,
        clickhouse_select=clickhouse_select,
    )


def _text_search_query(pg_schema: str, term_literal: str) -> AnalyticsBenchmarkQuery:
    postgres_sql = f"""
WITH texto_historico AS (
    SELECT
        EXTRACT(YEAR FROM p.fecha_pedido)::BIGINT AS anio,
        c.sector,
        pr.familia,
        c.id AS cliente_id,
        p.id AS pedido_id,
        lp.cantidad * lp.precio_unitario AS importe_linea,
        p.observaciones || ' ' || lp.descripcion || ' ' || pr.nombre AS texto_busqueda
    FROM {pg_schema}.pedidos p
    JOIN {pg_schema}.clientes c ON c.id = p.cliente_id
    JOIN {pg_schema}.lineas_pedido lp ON lp.pedido_id = p.id
    JOIN {pg_schema}.productos pr ON pr.id = lp.producto_id
),
coincidencias AS (
    SELECT
        anio,
        sector,
        familia,
        cliente_id,
        pedido_id,
        importe_linea
    FROM texto_historico
    WHERE texto_busqueda ILIKE '%' || {term_literal} || '%'
),
resumen AS (
    SELECT
        anio,
        sector,
        familia,
        COUNT(DISTINCT pedido_id) AS pedidos_distintos,
        COUNT(DISTINCT cliente_id) AS clientes_distintos,
        SUM(importe_linea) AS facturacion
    FROM coincidencias
    GROUP BY anio, sector, familia
)
SELECT concat_ws(
    '|',
    anio::TEXT,
    sector,
    familia,
    pedidos_distintos::TEXT,
    clientes_distintos::TEXT,
    FLOOR(facturacion * 100)::TEXT
) AS row_signature
FROM resumen
"""
    clickhouse_ctes = (
        """
texto_historico AS (
    SELECT
        toYear(p.fecha_pedido) AS anio,
        c.sector AS sector,
        pr.familia AS familia,
        c.id AS cliente_id,
        p.id AS pedido_id,
        lp.cantidad * lp.precio_unitario AS importe_linea,
        concat(p.observaciones, ' ', lp.descripcion, ' ', pr.nombre) AS texto_busqueda
    FROM pedidos AS p
    INNER JOIN clientes AS c ON c.id = p.cliente_id
    INNER JOIN lineas_pedido AS lp ON lp.pedido_id = p.id
    INNER JOIN productos AS pr ON pr.id = lp.producto_id
)""",
        f"""
coincidencias AS (
    SELECT
        anio,
        sector,
        familia,
        cliente_id,
        pedido_id,
        importe_linea
    FROM texto_historico
    WHERE positionCaseInsensitive(texto_busqueda, {term_literal}) > 0
)""",
        """
resumen AS (
    SELECT
        anio,
        sector,
        familia,
        uniqExact(pedido_id) AS pedidos_distintos,
        uniqExact(cliente_id) AS clientes_distintos,
        sum(importe_linea) AS facturacion
    FROM coincidencias
    GROUP BY anio, sector, familia
)""",
    )
    clickhouse_select = """
SELECT concat(
    toString(anio),
    '|', sector,
    '|', familia,
    '|', toString(pedidos_distintos),
    '|', toString(clientes_distintos),
    '|', toString(toInt64(floor(facturacion * 100)))
) AS row_signature
FROM resumen
"""
    return AnalyticsBenchmarkQuery(
        name="02_busqueda_textual_historica",
        postgres_sql=postgres_sql,
        clickhouse_ctes=clickhouse_ctes,
        clickhouse_select=clickhouse_select,
    )


def _sensor_activity_query(pg_schema: str) -> AnalyticsBenchmarkQuery:
    postgres_sql = f"""
WITH lecturas_enriquecidas AS (
    SELECT
        date_trunc('hour', ls.fecha_lectura) AS hora,
        m.codigo_maquina,
        m.area,
        pr.modelo_transformador,
        op.id AS orden_produccion_id,
        ls.temperatura,
        ls.consumo_kw,
        ls.fuera_rango,
        CASE
            WHEN ls.temperatura > 130 OR ls.vibracion > 10 OR ls.consumo_kw > 300 THEN 1
            ELSE 0
        END AS lectura_critica
    FROM {pg_schema}.lecturas_sensores ls
    JOIN {pg_schema}.maquinas m ON m.id = ls.maquina_id
    JOIN {pg_schema}.ordenes_produccion op ON op.id = ls.orden_produccion_id
    JOIN {pg_schema}.productos pr ON pr.id = op.producto_id
),
resumen AS (
    SELECT
        hora,
        codigo_maquina,
        area,
        modelo_transformador,
        COUNT(*) AS lecturas,
        COUNT(DISTINCT orden_produccion_id) AS ordenes_distintas,
        SUM(temperatura) AS temperatura_total,
        MAX(consumo_kw) AS consumo_kw_maximo,
        SUM(fuera_rango)::BIGINT AS lecturas_fuera_rango,
        SUM(lectura_critica)::BIGINT AS lecturas_criticas
    FROM lecturas_enriquecidas
    GROUP BY hora, codigo_maquina, area, modelo_transformador
)
SELECT concat_ws(
    '|',
    to_char(hora AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS'),
    codigo_maquina,
    area,
    modelo_transformador,
    lecturas::TEXT,
    ordenes_distintas::TEXT,
    FLOOR(temperatura_total * 100)::TEXT,
    FLOOR(consumo_kw_maximo * 100)::TEXT,
    lecturas_fuera_rango::TEXT,
    lecturas_criticas::TEXT
) AS row_signature
FROM resumen
"""
    clickhouse_ctes = (
        """
lecturas_enriquecidas AS (
    SELECT
        toStartOfHour(ls.fecha_lectura) AS hora,
        m.codigo_maquina AS codigo_maquina,
        m.area AS area,
        pr.modelo_transformador AS modelo_transformador,
        op.id AS orden_produccion_id,
        ls.temperatura AS temperatura,
        ls.consumo_kw AS consumo_kw,
        ls.fuera_rango AS fuera_rango,
        if(ls.temperatura > 130 OR ls.vibracion > 10 OR ls.consumo_kw > 300, 1, 0) AS lectura_critica
    FROM lecturas_sensores AS ls
    INNER JOIN maquinas AS m ON m.id = ls.maquina_id
    INNER JOIN ordenes_produccion AS op ON op.id = ls.orden_produccion_id
    INNER JOIN productos AS pr ON pr.id = op.producto_id
)""",
        """
resumen AS (
    SELECT
        hora,
        codigo_maquina,
        area,
        modelo_transformador,
        count() AS lecturas,
        uniqExact(orden_produccion_id) AS ordenes_distintas,
        sum(temperatura) AS temperatura_total,
        max(consumo_kw) AS consumo_kw_maximo,
        sum(fuera_rango) AS lecturas_fuera_rango,
        sum(lectura_critica) AS lecturas_criticas
    FROM lecturas_enriquecidas
    GROUP BY hora, codigo_maquina, area, modelo_transformador
)""",
    )
    clickhouse_select = """
SELECT concat(
    toString(hora),
    '|', codigo_maquina,
    '|', area,
    '|', modelo_transformador,
    '|', toString(lecturas),
    '|', toString(ordenes_distintas),
    '|', toString(toInt64(floor(temperatura_total * 100))),
    '|', toString(toInt64(floor(consumo_kw_maximo * 100))),
    '|', toString(lecturas_fuera_rango),
    '|', toString(lecturas_criticas)
) AS row_signature
FROM resumen
"""
    return AnalyticsBenchmarkQuery(
        name="03_sensores_por_hora_maquina_orden",
        postgres_sql=postgres_sql,
        clickhouse_ctes=clickhouse_ctes,
        clickhouse_select=clickhouse_select,
    )


def _client_activity_query(pg_schema: str) -> AnalyticsBenchmarkQuery:
    postgres_sql = f"""
WITH actividad_cliente AS (
    SELECT
        c.id AS cliente_id,
        c.nombre,
        c.sector,
        p.id AS pedido_id,
        p.fecha_pedido,
        pr.familia,
        lp.cantidad * lp.precio_unitario AS importe_linea,
        lp.cantidad * (lp.precio_unitario - lp.coste_unitario) AS margen_linea
    FROM {pg_schema}.clientes c
    JOIN {pg_schema}.pedidos p ON p.cliente_id = c.id
    JOIN {pg_schema}.lineas_pedido lp ON lp.pedido_id = p.id
    JOIN {pg_schema}.productos pr ON pr.id = lp.producto_id
),
resumen_cliente AS (
    SELECT
        cliente_id,
        nombre,
        sector,
        COUNT(DISTINCT pedido_id) AS pedidos_distintos,
        COUNT(DISTINCT familia) AS familias_distintas,
        MAX(fecha_pedido) AS ultimo_pedido,
        SUM(importe_linea) AS facturacion,
        SUM(margen_linea) AS margen
    FROM actividad_cliente
    GROUP BY cliente_id, nombre, sector
    HAVING COUNT(DISTINCT pedido_id) >= 3
       AND SUM(importe_linea) > 10000
)
SELECT concat_ws(
    '|',
    cliente_id::TEXT,
    nombre,
    sector,
    pedidos_distintos::TEXT,
    familias_distintas::TEXT,
    to_char(ultimo_pedido AT TIME ZONE 'UTC', 'YYYY-MM-DD'),
    FLOOR(facturacion * 100)::TEXT,
    FLOOR(margen * 100)::TEXT
) AS row_signature
FROM resumen_cliente
"""
    clickhouse_ctes = (
        """
actividad_cliente AS (
    SELECT
        c.id AS cliente_id,
        c.nombre AS nombre,
        c.sector AS sector,
        p.id AS pedido_id,
        p.fecha_pedido AS fecha_pedido,
        pr.familia AS familia,
        lp.cantidad * lp.precio_unitario AS importe_linea,
        lp.cantidad * (lp.precio_unitario - lp.coste_unitario) AS margen_linea
    FROM clientes AS c
    INNER JOIN pedidos AS p ON p.cliente_id = c.id
    INNER JOIN lineas_pedido AS lp ON lp.pedido_id = p.id
    INNER JOIN productos AS pr ON pr.id = lp.producto_id
)""",
        """
resumen_cliente AS (
    SELECT
        cliente_id,
        nombre,
        sector,
        uniqExact(pedido_id) AS pedidos_distintos,
        uniqExact(familia) AS familias_distintas,
        max(fecha_pedido) AS ultimo_pedido,
        sum(importe_linea) AS facturacion,
        sum(margen_linea) AS margen
    FROM actividad_cliente
    GROUP BY cliente_id, nombre, sector
    HAVING uniqExact(pedido_id) >= 3
       AND sum(importe_linea) > 10000
)""",
    )
    clickhouse_select = """
SELECT concat(
    toString(cliente_id),
    '|', nombre,
    '|', sector,
    '|', toString(pedidos_distintos),
    '|', toString(familias_distintas),
    '|', toString(toDate(ultimo_pedido)),
    '|', toString(toInt64(floor(facturacion * 100))),
    '|', toString(toInt64(floor(margen * 100)))
) AS row_signature
FROM resumen_cliente
"""
    return AnalyticsBenchmarkQuery(
        name="04_top_clientes_actividad_relevante",
        postgres_sql=postgres_sql,
        clickhouse_ctes=clickhouse_ctes,
        clickhouse_select=clickhouse_select,
    )


def _quality_traceability_query(pg_schema: str) -> AnalyticsBenchmarkQuery:
    postgres_sql = f"""
WITH trazabilidad AS (
    SELECT
        date_trunc('month', nc.fecha_deteccion) AS mes,
        prov.nombre AS proveedor,
        prov.pais AS pais_proveedor,
        mat.familia AS familia_material,
        nc.id AS no_conformidad_id,
        nc.severidad,
        op.id AS orden_produccion_id,
        cm.coste_consumido,
        lm.coste_total,
        nc.coste_estimado
    FROM {pg_schema}.no_conformidades nc
    JOIN {pg_schema}.ordenes_produccion op ON op.id = nc.orden_produccion_id
    JOIN {pg_schema}.consumos_material cm ON cm.orden_produccion_id = op.id
    JOIN {pg_schema}.lotes_material lm ON lm.id = cm.lote_material_id
    JOIN {pg_schema}.materiales mat ON mat.id = lm.material_id
    JOIN {pg_schema}.proveedores prov ON prov.id = lm.proveedor_id
),
resumen AS (
    SELECT
        mes,
        proveedor,
        pais_proveedor,
        familia_material,
        COUNT(DISTINCT no_conformidad_id) AS no_conformidades,
        COUNT(DISTINCT orden_produccion_id) AS ordenes_afectadas,
        SUM(severidad)::BIGINT AS severidad_total,
        SUM(coste_estimado) AS coste_calidad,
        SUM(coste_consumido) AS coste_material_consumido,
        MAX(coste_total) AS lote_mayor_coste
    FROM trazabilidad
    GROUP BY mes, proveedor, pais_proveedor, familia_material
)
SELECT concat_ws(
    '|',
    to_char(mes AT TIME ZONE 'UTC', 'YYYY-MM-DD'),
    proveedor,
    pais_proveedor,
    familia_material,
    no_conformidades::TEXT,
    ordenes_afectadas::TEXT,
    severidad_total::TEXT,
    FLOOR(coste_calidad * 100)::TEXT,
    FLOOR(coste_material_consumido * 100)::TEXT,
    FLOOR(lote_mayor_coste * 100)::TEXT
) AS row_signature
FROM resumen
"""
    clickhouse_ctes = (
        """
trazabilidad AS (
    SELECT
        toStartOfMonth(nc.fecha_deteccion) AS mes,
        prov.nombre AS proveedor,
        prov.pais AS pais_proveedor,
        mat.familia AS familia_material,
        nc.id AS no_conformidad_id,
        nc.severidad AS severidad,
        op.id AS orden_produccion_id,
        cm.coste_consumido AS coste_consumido,
        lm.coste_total AS coste_total,
        nc.coste_estimado AS coste_estimado
    FROM no_conformidades AS nc
    INNER JOIN ordenes_produccion AS op ON op.id = nc.orden_produccion_id
    INNER JOIN consumos_material AS cm ON cm.orden_produccion_id = op.id
    INNER JOIN lotes_material AS lm ON lm.id = cm.lote_material_id
    INNER JOIN materiales AS mat ON mat.id = lm.material_id
    INNER JOIN proveedores AS prov ON prov.id = lm.proveedor_id
)""",
        """
resumen AS (
    SELECT
        mes,
        proveedor,
        pais_proveedor,
        familia_material,
        uniqExact(no_conformidad_id) AS no_conformidades,
        uniqExact(orden_produccion_id) AS ordenes_afectadas,
        sum(severidad) AS severidad_total,
        sum(coste_estimado) AS coste_calidad,
        sum(coste_consumido) AS coste_material_consumido,
        max(coste_total) AS lote_mayor_coste
    FROM trazabilidad
    GROUP BY mes, proveedor, pais_proveedor, familia_material
)""",
    )
    clickhouse_select = """
SELECT concat(
    toString(toDate(mes)),
    '|', proveedor,
    '|', pais_proveedor,
    '|', familia_material,
    '|', toString(no_conformidades),
    '|', toString(ordenes_afectadas),
    '|', toString(severidad_total),
    '|', toString(toInt64(floor(coste_calidad * 100))),
    '|', toString(toInt64(floor(coste_material_consumido * 100))),
    '|', toString(toInt64(floor(lote_mayor_coste * 100)))
) AS row_signature
FROM resumen
"""
    return AnalyticsBenchmarkQuery(
        name="05_trazabilidad_calidad",
        postgres_sql=postgres_sql,
        clickhouse_ctes=clickhouse_ctes,
        clickhouse_select=clickhouse_select,
    )


def _postgres_signature_sql(canonical_query_sql: str) -> str:
    return f"""
WITH canonical AS (
{canonical_query_sql}
)
SELECT COUNT(*)::TEXT || '|' || COALESCE(
    md5(string_agg(md5(row_signature), '' ORDER BY md5(row_signature))),
    md5('')
)
FROM canonical;
"""


def _clickhouse_signature_sql(
    query: AnalyticsBenchmarkQuery,
    clickhouse_database: str,
) -> str:
    ctes = [
        _clickhouse_live_table_cte(clickhouse_database, table_name)
        for table_name in TABLE_COLUMNS
    ]
    ctes.extend(query.clickhouse_ctes)
    ctes.append(f"canonical AS (\n{query.clickhouse_select}\n)")
    return (
        "WITH\n"
        + ",\n".join(ctes)
        + """
SELECT concat(
    toString(count()),
    '|',
    lower(hex(MD5(arrayStringConcat(arraySort(groupArray(lower(hex(MD5(row_signature))))), ''))))
)
FROM canonical
"""
    )


def _clickhouse_live_table_cte(clickhouse_database: str, table_name: str) -> str:
    return (
        f"{table_name} AS ("
        f"SELECT * FROM {_quote_clickhouse_identifier(clickhouse_database)}."
        f"{_quote_clickhouse_identifier(table_name)} FINAL WHERE deleted = 0"
        ")"
    )


def _postgres_table_counts_sql(
    schema_name: str,
    table_specs: Sequence[IndustrialTableSpec],
) -> str:
    selects = [
        (
            f"SELECT {_sql_literal(table.name)} AS table_name, "
            f"COUNT(*)::BIGINT AS row_count "
            f"FROM {schema_name}.{_quote_postgres_identifier(table.name)}"
        )
        for table in table_specs
    ]
    return (
        "SELECT table_name || '|' || row_count::TEXT\n"
        "FROM (\n"
        + "\nUNION ALL\n".join(selects)
        + "\n) table_counts\n"
        "ORDER BY table_name;\n"
    )


def _clickhouse_live_table_counts_sql(
    clickhouse_database: str,
    table_specs: Sequence[IndustrialTableSpec],
) -> str:
    database_name = _quote_clickhouse_identifier(clickhouse_database)
    selects = [
        (
            f"SELECT {_sql_literal(table.name)} AS table_name, "
            f"count() AS row_count "
            f"FROM {database_name}.{_quote_clickhouse_identifier(table.name)} "
            "FINAL WHERE deleted = 0"
        )
        for table in table_specs
    ]
    return (
        "SELECT concat(table_name, '|', toString(row_count))\n"
        "FROM (\n"
        + "\nUNION ALL\n".join(selects)
        + "\n) table_counts\n"
        "ORDER BY table_name\n"
    )


def _parse_table_count_rows(output: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        parts = line.split("|", 1)
        if len(parts) != 2:
            raise AnalyticsDemoError(f"Conteo por tabla inválido: {line}")

        counts[parts[0]] = int(parts[1])

    if counts:
        return counts

    raise AnalyticsDemoError("No se pudieron leer conteos por tabla")


def _table_progress_rows(
    expected_table_counts: dict[str, int],
    actual_table_counts: dict[str, int],
) -> list[TableSyncProgress]:
    return [
        TableSyncProgress(
            table_name=table_name,
            postgres_rows=postgres_rows,
            clickhouse_rows=actual_table_counts.get(table_name, 0),
        )
        for table_name, postgres_rows in expected_table_counts.items()
    ]


def _assert_table_counts_match(progress_rows: list[TableSyncProgress]) -> None:
    pending_rows = [row for row in progress_rows if row.delta_rows != 0]
    if not pending_rows:
        return

    raise AnalyticsDemoError(
        "Filas vivas pendientes: " + _format_pending_table_progress(pending_rows)
    )


def _print_convergence_progress_unavailable(
    *,
    label: str,
    elapsed_seconds: int,
    progress_error: Exception,
    last_error: Exception | None,
) -> None:
    print(
        "[analytics-demo] progreso "
        f"fase={label} "
        f"t={elapsed_seconds}s "
        "estado=conteos_no_disponibles "
        f"último_error={_compact_error_message(last_error)} "
        f"progreso_error={_compact_error_message(progress_error)}",
        flush=True,
    )


def _print_convergence_progress(
    *,
    label: str,
    elapsed_seconds: int,
    progress_rows: list[TableSyncProgress],
    last_error: Exception | None,
) -> None:
    print(
        "[analytics-demo] progreso "
        f"fase={label} "
        f"t={elapsed_seconds}s "
        f"{_format_table_progress_summary(progress_rows)} "
        f"último_error={_compact_error_message(last_error)}",
        flush=True,
    )


def _format_table_progress_summary(progress_rows: list[TableSyncProgress]) -> str:
    postgres_total = sum(row.postgres_rows for row in progress_rows)
    clickhouse_total = sum(row.clickhouse_rows for row in progress_rows)
    pending_rows = [row for row in progress_rows if row.delta_rows != 0]
    summary = (
        f"filas_vivas={clickhouse_total}/{postgres_total} "
        f"tablas_pendientes={len(pending_rows)}/{len(progress_rows)}"
    )
    if not pending_rows:
        return f"{summary} detalle=filas vivas coinciden; esperando firmas"

    return f"{summary} detalle={_format_pending_table_progress(pending_rows)}"


def _format_pending_table_progress(
    pending_rows: list[TableSyncProgress],
) -> str:
    sorted_rows = sorted(
        pending_rows,
        key=lambda row: abs(row.delta_rows),
        reverse=True,
    )
    visible_rows = sorted_rows[:PROGRESS_TABLE_LIMIT]
    hidden_count = len(sorted_rows) - len(visible_rows)
    detail = ", ".join(_format_table_sync_progress(row) for row in visible_rows)
    if hidden_count <= 0:
        return detail

    return f"{detail}, +{hidden_count} tablas"


def _format_table_sync_progress(row: TableSyncProgress) -> str:
    direction = "faltan" if row.delta_rows > 0 else "sobran"
    return (
        f"{row.table_name}={row.clickhouse_rows}/{row.postgres_rows} "
        f"({direction} {abs(row.delta_rows)})"
    )


def _compact_error_message(error: Exception | None) -> str:
    if error is None:
        return "sin error"

    message = " ".join(str(error).split())
    if len(message) <= 180:
        return message

    return message[:177] + "..."


def _assert_signature_sets_match(
    postgres_signatures: list[QuerySignature],
    clickhouse_signatures: list[QuerySignature],
) -> None:
    postgres_by_name = {signature.name: signature for signature in postgres_signatures}
    clickhouse_by_name = {signature.name: signature for signature in clickhouse_signatures}
    if set(postgres_by_name) != set(clickhouse_by_name):
        raise AnalyticsDemoError("Los motores no devolvieron las mismas consultas")

    mismatches = [
        _signature_mismatch(postgres_by_name[name], clickhouse_by_name[name])
        for name in sorted(postgres_by_name)
        if _signature_mismatch(postgres_by_name[name], clickhouse_by_name[name])
    ]
    if not mismatches:
        return

    raise AnalyticsDemoError("Diferencias de convergencia: " + "; ".join(mismatches))


def _signature_mismatch(
    postgres_signature: QuerySignature,
    clickhouse_signature: QuerySignature,
) -> str | None:
    if postgres_signature.row_count != clickhouse_signature.row_count:
        return (
            f"{postgres_signature.name} filas "
            f"{postgres_signature.row_count}!={clickhouse_signature.row_count}"
        )

    if postgres_signature.signature == clickhouse_signature.signature:
        return None

    return (
        f"{postgres_signature.name} firma "
        f"{postgres_signature.signature}!={clickhouse_signature.signature}"
    )


def _assert_signatures_changed(
    signatures: list[QuerySignature],
    initial_signatures: dict[str, QuerySignature] | None,
    *,
    require_changed: bool,
) -> None:
    if not require_changed:
        return

    if initial_signatures is None:
        raise AnalyticsDemoError(
            "No hay firmas iniciales. Ejecuta antes analytics-demo-wait-snapshot."
        )

    unchanged_queries = [
        signature.name
        for signature in signatures
        if _same_signature(signature, initial_signatures.get(signature.name))
    ]
    if not unchanged_queries:
        return

    raise AnalyticsDemoError(
        "Las firmas todavía no han cambiado frente a la fase inicial: "
        + ", ".join(unchanged_queries)
    )


def _same_signature(
    current_signature: QuerySignature,
    initial_signature: QuerySignature | None,
) -> bool:
    if initial_signature is None:
        return False

    return (
        current_signature.row_count == initial_signature.row_count
        and current_signature.signature == initial_signature.signature
    )


def _signature_state(signatures: list[QuerySignature]) -> dict[str, dict[str, Any]]:
    return {
        signature.name: {
            "row_count": signature.row_count,
            "signature": signature.signature,
        }
        for signature in signatures
    }


def _load_optional_initial_signatures(
    state: dict[str, Any],
) -> dict[str, QuerySignature] | None:
    raw_signatures = state.get("initial_signatures")
    if raw_signatures is None:
        return None

    return _load_signature_state(raw_signatures)


def _load_signature_state(raw_signatures: Any) -> dict[str, QuerySignature]:
    if not isinstance(raw_signatures, dict):
        raise AnalyticsDemoError("Las firmas guardadas deben ser un objeto JSON")

    signatures: dict[str, QuerySignature] = {}
    for name, raw_signature in raw_signatures.items():
        if not isinstance(name, str) or not isinstance(raw_signature, dict):
            raise AnalyticsDemoError("Las firmas guardadas tienen formato inválido")

        signatures[name] = QuerySignature(
            name=name,
            row_count=int(raw_signature["row_count"]),
            signature=str(raw_signature["signature"]),
        )

    return signatures


def _parse_signature_output(output: str, query_name: str) -> tuple[int, str]:
    line = output.strip()
    if not line:
        raise AnalyticsDemoError(f"{query_name}: la consulta no devolvió firma")

    parts = line.split("|", 1)
    if len(parts) == 2:
        return int(parts[0]), parts[1]

    raise AnalyticsDemoError(f"{query_name}: firma inválida: {line}")


def _print_benchmark_result(result: EngineBenchmarkResult) -> None:
    print(
        "[analytics-demo] "
        f"fase={result.phase} "
        f"motor={result.engine} "
        f"consulta={result.query_name} "
        f"tiempo_ms={result.elapsed_ms:.1f} "
        f"filas={result.row_count} "
        f"firma={result.signature}",
        flush=True,
    )


def _print_speedup_summary(results: list[EngineBenchmarkResult]) -> None:
    total_by_engine: dict[str, float] = {}
    for result in results:
        total_by_engine[result.engine] = (
            total_by_engine.get(result.engine, 0.0) + result.elapsed_ms
        )

    postgres_total = total_by_engine.get("PostgreSQL", 0.0)
    clickhouse_total = total_by_engine.get("ClickHouse", 0.0)
    if clickhouse_total <= 0:
        raise AnalyticsDemoError("El tiempo total de ClickHouse no es válido")

    speedup = postgres_total / clickhouse_total
    print(
        "[analytics-demo] resumen "
        f"postgres_ms={postgres_total:.1f} "
        f"clickhouse_ms={clickhouse_total:.1f} "
        f"factor_clickhouse={speedup:.1f}x",
        flush=True,
    )


def _print_signature_summary(
    label: str,
    signatures: list[QuerySignature],
) -> None:
    print(f"[analytics-demo] convergencia={label}", flush=True)
    for signature in signatures:
        print(
            "[analytics-demo]   "
            f"consulta={signature.name} "
            f"filas={signature.row_count} "
            f"firma={signature.signature}",
            flush=True,
        )


def _load_environment() -> dict[str, str]:
    env = {
        "POSTGRES_DB": "cdc_sync",
        "POSTGRES_USER": "cdc_sync",
        "POSTGRES_PASSWORD": "cdc_sync",
        "API_PORT": "8000",
        "CONNECT_PORT": "8083",
        "CLICKHOUSE_DB": "cdc_sync_analytics",
        "CLICKHOUSE_USER": "cdc_sync",
        "CLICKHOUSE_PASSWORD": "cdc_sync",
    }
    env.update(load_environment())
    env.update({key: value for key, value in os.environ.items() if value is not None})
    return env


def _run(
    command: list[str],
    *,
    check: bool = True,
    timeout_seconds: int | None = None,
) -> str:
    try:
        result = subprocess.run(
            command,
            cwd=ROOT_DIR,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        raise AnalyticsDemoError(
            f"Timeout ejecutando: {' '.join(command)}"
        ) from exc

    if check and result.returncode != 0:
        raise AnalyticsDemoError(
            f"Falló el comando: {' '.join(command)}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )

    return result.stdout + result.stderr if result.returncode != 0 else result.stdout


def _wait_until(
    label: str,
    predicate,
    *,
    attempts: int = 30,
    delay_seconds: int = 2,
) -> None:
    last_error: Exception | None = None
    for _ in range(attempts):
        try:
            if predicate():
                return
        except Exception as exc:
            last_error = exc

        time.sleep(delay_seconds)

    raise AnalyticsDemoError(f"{label} no está listo. Último error: {last_error}")


def _http_get(url: str) -> Any:
    try:
        with urlopen(url, timeout=10) as response:
            body = response.read().decode("utf-8")
    except (HTTPError, URLError) as exc:
        raise AnalyticsDemoError(f"No se pudo consultar {url}") from exc

    if not body:
        return {}

    return json.loads(body)


def _quote_postgres_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _quote_clickhouse_identifier(identifier: str) -> str:
    return "`" + identifier.replace("`", "``") + "`"


def _sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _container_name(worker_id: str) -> str:
    return f"cdc-sync-demo-worker-{worker_id}"


def _sync_config_name(module: IndustrialWorkerModuleSpec) -> str:
    return f"{SYNC_CONFIG_NAME_PREFIX} - {module.worker_id}"


def _parse_worker_ids(raw_worker_ids: str) -> list[str]:
    worker_ids = [
        worker_id.strip()
        for worker_id in raw_worker_ids.split(",")
        if worker_id.strip()
    ]
    return _validate_worker_ids(worker_ids, "ANALYTICS_DEMO_WORKER_IDS")


def _validate_worker_ids(worker_ids: list[str], label: str) -> list[str]:
    if not worker_ids:
        raise AnalyticsDemoError(f"{label} debe incluir al menos un worker")

    duplicated_worker_ids = {
        worker_id
        for worker_id in worker_ids
        if worker_ids.count(worker_id) > 1
    }
    if duplicated_worker_ids:
        raise AnalyticsDemoError(
            f"{label} contiene workers duplicados: "
            + ", ".join(sorted(duplicated_worker_ids))
        )

    return worker_ids


def _split_container_state(output: str, label: str) -> tuple[str, str, str, str]:
    parts = output.split("|", 3)
    if len(parts) == 4:
        return parts[0], parts[1], parts[2], parts[3]

    raise AnalyticsDemoError(
        f"No se pudo interpretar el estado Docker de {label}: {output}"
    )


def _print_step(message: str) -> None:
    print(f"[analytics-demo] {message}", flush=True)


def _print_ok(message: str) -> None:
    print(f"[analytics-demo] OK: {message}", flush=True)


def build_parser() -> argparse.ArgumentParser:
    env = _load_environment()
    parser = argparse.ArgumentParser(
        description="Demo OLTP -> CDC -> OLAP del dataset industrial analítico.",
    )
    parser.add_argument(
        "--schema",
        default=env.get("ANALYTICS_DATASET_SCHEMA", DEFAULT_SCHEMA),
    )
    parser.add_argument(
        "--worker-ids",
        default=env.get("ANALYTICS_DEMO_WORKER_IDS", DEFAULT_WORKER_IDS),
    )
    parser.add_argument(
        "--state-file",
        default=env.get("ANALYTICS_DEMO_STATE_FILE", DEFAULT_STATE_FILE),
    )
    parser.add_argument(
        "--term",
        default=env.get("ANALYTICS_DATASET_TERM", DEFAULT_SEARCH_TERM),
    )
    parser.add_argument(
        "--clickhouse-database",
        default=env.get("CLICKHOUSE_DB", "cdc_sync_analytics"),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in (
        "configure",
        "materialize",
        "wait-snapshot",
        "benchmark",
        "changes",
        "wait-cdc",
        "benchmark-after",
        "reset",
    ):
        subparsers.add_parser(command)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    runner = IndustrialAnalyticsDemoRunner(args)
    commands = {
        "configure": runner.configure,
        "materialize": runner.materialize,
        "wait-snapshot": runner.wait_snapshot,
        "benchmark": runner.benchmark,
        "changes": runner.changes,
        "wait-cdc": runner.wait_cdc,
        "benchmark-after": runner.benchmark_after,
        "reset": runner.reset,
    }
    try:
        commands[args.command]()
        return 0
    except AnalyticsDemoError as exc:
        print(f"[analytics-demo] ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

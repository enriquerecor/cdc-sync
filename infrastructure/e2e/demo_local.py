#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_STATE_FILE = ".tmp/e2e-demo-state.json"
DEFAULT_WORKER_IDS = "crm-worker,sales-worker,operations-worker"
DEFAULT_ASSERT_TIMEOUT_SECONDS = 120
ASSERT_RETRY_DELAY_SECONDS = 5
WORKER_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
POSTGRES_SCHEMA_FILES = (
    "infrastructure/postgresql/init/003-erp-crm-schema.sql",
    "infrastructure/postgresql/init/004-erp-crm-seed.sql",
)


class DemoError(RuntimeError):
    pass


class ReconciliationError(DemoError):
    pass


@dataclass(frozen=True)
class ColumnSpec:
    name: str
    clickhouse_type: str
    nullable: bool
    value_kind: str


@dataclass(frozen=True)
class TableSpec:
    name: str
    columns: tuple[ColumnSpec, ...]
    primary_key: tuple[str, ...] = ("id",)

    @property
    def topic(self) -> str:
        return f"cdc_sync.public.{self.name}"


@dataclass(frozen=True)
class WorkerModuleSpec:
    worker_id: str
    name: str
    description: str
    tables: tuple[TableSpec, ...]


UINT_ID = ColumnSpec("id", "UInt64", False, "uint")
TEXT = "text"
UINT = "uint"
DECIMAL = "decimal"


CRM_TABLES = (
    TableSpec(
        "crm_accounts",
        (
            UINT_ID,
            ColumnSpec("account_code", "String", False, TEXT),
            ColumnSpec("name", "String", False, TEXT),
            ColumnSpec("segment", "String", False, TEXT),
            ColumnSpec("status", "String", False, TEXT),
            ColumnSpec("annual_revenue", "Decimal(12, 2)", False, DECIMAL),
        ),
    ),
    TableSpec(
        "crm_contacts",
        (
            UINT_ID,
            ColumnSpec("account_id", "UInt64", False, UINT),
            ColumnSpec("contact_code", "String", False, TEXT),
            ColumnSpec("email", "String", False, TEXT),
            ColumnSpec("full_name", "String", False, TEXT),
            ColumnSpec("role_title", "String", False, TEXT),
            ColumnSpec("lifecycle_stage", "String", False, TEXT),
        ),
    ),
    TableSpec(
        "crm_opportunities",
        (
            UINT_ID,
            ColumnSpec("account_id", "UInt64", False, UINT),
            ColumnSpec("opportunity_code", "String", False, TEXT),
            ColumnSpec("title", "String", False, TEXT),
            ColumnSpec("stage", "String", False, TEXT),
            ColumnSpec("expected_amount", "Decimal(12, 2)", False, DECIMAL),
        ),
    ),
    TableSpec(
        "crm_activities",
        (
            UINT_ID,
            ColumnSpec("account_id", "UInt64", False, UINT),
            ColumnSpec("contact_id", "UInt64", True, UINT),
            ColumnSpec("activity_code", "String", False, TEXT),
            ColumnSpec("activity_type", "String", False, TEXT),
            ColumnSpec("subject", "String", False, TEXT),
            ColumnSpec("status", "String", False, TEXT),
        ),
    ),
)

SALES_TABLES = (
    TableSpec(
        "sales_orders",
        (
            UINT_ID,
            ColumnSpec("account_id", "UInt64", False, UINT),
            ColumnSpec("contact_id", "UInt64", True, UINT),
            ColumnSpec("order_number", "String", False, TEXT),
            ColumnSpec("status", "String", False, TEXT),
            ColumnSpec("total_amount", "Decimal(12, 2)", False, DECIMAL),
        ),
    ),
    TableSpec(
        "sales_order_lines",
        (
            UINT_ID,
            ColumnSpec("order_id", "UInt64", False, UINT),
            ColumnSpec("product_id", "UInt64", False, UINT),
            ColumnSpec("line_code", "String", False, TEXT),
            ColumnSpec("quantity", "Decimal(12, 2)", False, DECIMAL),
            ColumnSpec("unit_price", "Decimal(10, 2)", False, DECIMAL),
            ColumnSpec("line_status", "String", False, TEXT),
        ),
    ),
    TableSpec(
        "sales_invoices",
        (
            UINT_ID,
            ColumnSpec("order_id", "UInt64", False, UINT),
            ColumnSpec("invoice_number", "String", False, TEXT),
            ColumnSpec("status", "String", False, TEXT),
            ColumnSpec("amount_due", "Decimal(12, 2)", False, DECIMAL),
        ),
    ),
    TableSpec(
        "sales_payments",
        (
            UINT_ID,
            ColumnSpec("invoice_id", "UInt64", False, UINT),
            ColumnSpec("payment_reference", "String", False, TEXT),
            ColumnSpec("status", "String", False, TEXT),
            ColumnSpec("amount_paid", "Decimal(12, 2)", False, DECIMAL),
        ),
    ),
)

OPERATIONS_TABLES = (
    TableSpec(
        "ops_suppliers",
        (
            UINT_ID,
            ColumnSpec("supplier_code", "String", False, TEXT),
            ColumnSpec("name", "String", False, TEXT),
            ColumnSpec("status", "String", False, TEXT),
            ColumnSpec("rating_score", "Decimal(10, 2)", False, DECIMAL),
        ),
    ),
    TableSpec(
        "ops_products",
        (
            UINT_ID,
            ColumnSpec("supplier_id", "UInt64", False, UINT),
            ColumnSpec("sku", "String", False, TEXT),
            ColumnSpec("name", "String", False, TEXT),
            ColumnSpec("category", "String", False, TEXT),
            ColumnSpec("unit_cost", "Decimal(10, 2)", False, DECIMAL),
            ColumnSpec("status", "String", False, TEXT),
        ),
    ),
    TableSpec(
        "ops_warehouses",
        (
            UINT_ID,
            ColumnSpec("warehouse_code", "String", False, TEXT),
            ColumnSpec("name", "String", False, TEXT),
            ColumnSpec("region", "String", False, TEXT),
            ColumnSpec("capacity_units", "Decimal(12, 2)", False, DECIMAL),
            ColumnSpec("status", "String", False, TEXT),
        ),
    ),
    TableSpec(
        "ops_inventory_movements",
        (
            UINT_ID,
            ColumnSpec("product_id", "UInt64", False, UINT),
            ColumnSpec("warehouse_id", "UInt64", False, UINT),
            ColumnSpec("movement_code", "String", False, TEXT),
            ColumnSpec("movement_type", "String", False, TEXT),
            ColumnSpec("quantity", "Decimal(12, 2)", False, DECIMAL),
            ColumnSpec("reason", "String", False, TEXT),
        ),
    ),
)

MODULES_BY_WORKER_ID: dict[str, WorkerModuleSpec] = {
    "crm-worker": WorkerModuleSpec(
        worker_id="crm-worker",
        name="CRM",
        description="Sincroniza cuentas, contactos, oportunidades y actividades.",
        tables=CRM_TABLES,
    ),
    "sales-worker": WorkerModuleSpec(
        worker_id="sales-worker",
        name="Ventas y facturación",
        description="Sincroniza pedidos, líneas, facturas y pagos.",
        tables=SALES_TABLES,
    ),
    "operations-worker": WorkerModuleSpec(
        worker_id="operations-worker",
        name="Operaciones e inventario",
        description="Sincroniza proveedores, productos, almacenes y movimientos.",
        tables=OPERATIONS_TABLES,
    ),
}


class DemoRunner:
    def __init__(self) -> None:
        self.env = _load_environment()
        self.api_base_url = self.env.get("DEMO_API_BASE_URL") or (
            f"http://localhost:{self.env.get('API_PORT', '8000')}"
        )
        self.connect_base_url = (
            f"http://localhost:{self.env.get('CONNECT_PORT', '8083')}"
        )
        self.state_file = ROOT_DIR / self.env.get(
            "DEMO_STATE_FILE",
            DEFAULT_STATE_FILE,
        )

    def up(self) -> None:
        _print_step("Levantando infraestructura local")
        _run(
            [
                "docker",
                "compose",
                "up",
                "-d",
                "--build",
                "control-plane-postgres",
                "api",
                "postgres",
                "zookeeper",
                "kafka",
                "connect",
                "clickhouse",
            ]
        )
        self._wait_for_postgres()
        self._wait_for_kafka()
        self._wait_for_connect()
        self._wait_for_clickhouse()
        self._wait_for_api()
        self._apply_postgres_demo_schema()

    def migrate(self) -> None:
        _print_step("Aplicando migraciones del control plane")
        _run(["docker", "compose", "up", "-d", "--build", "control-plane-postgres", "api"])
        self._wait_for_control_plane_postgres()
        _run(["docker", "compose", "run", "--rm", "api", "alembic", "-c", "api/alembic.ini", "upgrade", "head"])
        self._wait_for_api()

    def configure(self) -> None:
        worker_ids = self._selected_worker_ids()
        _print_step("Creando configuración administrativa desde la API")
        self._wait_for_api()
        state = self._load_state()
        run_id = state.get("run_id") or uuid4().hex[:8]

        source_connection = self._get_or_create_source_connection()
        destination = self._get_or_create_destination()
        workers_by_identifier = self._list_by_key("/api/v1/workers", "worker_id")

        worker_state: dict[str, dict[str, Any]] = {}
        for worker_id in worker_ids:
            module = MODULES_BY_WORKER_ID[worker_id]
            worker = self._upsert_worker(
                module=module,
                existing_worker=workers_by_identifier.get(worker_id),
                run_id=run_id,
            )
            config = self._create_config(
                module=module,
                source_connection_id=source_connection["id"],
                destination_id=destination["id"],
                run_id=run_id,
            )
            assignment = self._request_json(
                "PUT",
                f"/api/v1/workers/{worker['id']}/config-assignment",
                {"config_id": config["id"]},
            )
            runtime_config = self._request_json(
                "GET",
                f"/workers/{worker_id}/config",
                None,
            )
            if not runtime_config.get("tables"):
                raise DemoError(
                    f"El worker '{worker_id}' no recibió tablas runtime habilitadas"
                )

            worker_state[worker_id] = {
                "id": worker["id"],
                "config_id": config["id"],
                "assignment": assignment,
                "kafka_group_id": worker["kafka_group_id"],
                "container_name": _container_name(worker_id),
                "tables": [table.name for table in module.tables],
            }

        state.update(
            {
                "run_id": run_id,
                "source_connection_id": source_connection["id"],
                "destination_id": destination["id"],
                "worker_ids": worker_ids,
                "workers": worker_state,
            }
        )
        self._save_state(state)
        _print_ok(f"Configuración guardada en {self.state_file.relative_to(ROOT_DIR)}")

    def materialize(self) -> None:
        state = self._require_state("source_connection_id")
        _print_step("Materializando conector Debezium desde el control plane")
        self._wait_for_api()
        self._wait_for_connect()
        materialized = self._request_json(
            "PUT",
            f"/api/v1/source-connections/{state['source_connection_id']}/cdc-connector",
            None,
        )
        connector_name = materialized["connector_name"]
        state["connector_name"] = connector_name
        state["captured_tables"] = list(materialized["captured_tables"])
        self._save_state(state)
        self._wait_for_connector(connector_name)
        _print_ok(f"Conector materializado: {connector_name}")

    def workers(self) -> None:
        state = self._require_state("workers")
        worker_containers = self._start_workers(
            self._state_worker_ids(state),
            "Arrancando workers stateless con WORKER_ID dinámico",
        )
        state["worker_containers"] = worker_containers
        self._save_state(state)
        _print_ok("Workers arrancados")

    def _start_workers(
        self,
        worker_ids: list[str],
        message: str,
    ) -> dict[str, str]:
        _print_step(message)
        self._wait_for_api()
        self._wait_for_kafka()
        self._wait_for_clickhouse()
        self._validate_runtime_configs(worker_ids)
        _run(["docker", "compose", "build", "worker"])

        worker_containers: dict[str, str] = {}
        for worker_id in worker_ids:
            container_name = _container_name(worker_id)
            self._remove_worker_container(container_name, report_missing=False)
            _run(
                [
                    "docker",
                    "compose",
                    "run",
                    "-d",
                    "--name",
                    container_name,
                    "--no-deps",
                    "-e",
                    f"WORKER_ID={worker_id}",
                    "worker",
                ]
            )
            self._wait_for_container_running(container_name)
            worker_containers[worker_id] = container_name

        return worker_containers

    def changes(self) -> None:
        state = self._require_state("worker_ids")
        _print_step("Aplicando cambios extensos en PostgreSQL OLTP")
        self._wait_for_postgres()
        self._reset_demo_rows()
        deleted_primary_keys = self._apply_demo_changes()
        state["deleted_primary_keys"] = deleted_primary_keys
        self._save_state(state)
        _print_ok("Cambios aplicados y claves borradas registradas")

    def assert_state(self) -> None:
        state = self._require_state("worker_ids", "deleted_primary_keys")
        _print_step("Reconciliando PostgreSQL y ClickHouse")
        deadline = time.monotonic() + int(
            self.env.get("DEMO_ASSERT_TIMEOUT_SECONDS", DEFAULT_ASSERT_TIMEOUT_SECONDS)
        )
        last_error: Exception | None = None

        while time.monotonic() <= deadline:
            try:
                live_row_counts = self._assert_live_rows(state)
                tombstone_counts = self._assert_deleted_tombstones(state)
                _print_reconciliation_summary(live_row_counts, tombstone_counts)
                _print_ok("PostgreSQL y ClickHouse están reconciliados")
                return
            except (DemoError, subprocess.CalledProcessError) as exc:
                last_error = exc
                time.sleep(ASSERT_RETRY_DELAY_SECONDS)

        diagnostics = self._diagnostics(state)
        raise DemoError(
            "ClickHouse no convergió antes del timeout.\n"
            f"Último error: {last_error}\n\n{diagnostics}"
        )

    def all(self) -> None:
        self.up()
        self.migrate()
        self.configure()
        self.materialize()
        self.workers()
        self.changes()
        self.assert_state()

    def _selected_worker_ids(self) -> list[str]:
        worker_ids = _parse_worker_ids(
            self.env.get("DEMO_WORKER_IDS", DEFAULT_WORKER_IDS),
            "DEMO_WORKER_IDS",
        )
        unsupported_worker_ids = [
            worker_id
            for worker_id in worker_ids
            if worker_id not in MODULES_BY_WORKER_ID
        ]
        if not unsupported_worker_ids:
            return worker_ids

        supported = ", ".join(MODULES_BY_WORKER_ID)
        unsupported = ", ".join(unsupported_worker_ids)
        raise DemoError(
            f"Workers de demo no soportados: {unsupported}. Valores válidos: {supported}"
        )

    def _state_worker_ids(self, state: dict[str, Any]) -> list[str]:
        worker_ids = state.get("worker_ids")
        if not isinstance(worker_ids, list) or not worker_ids:
            raise DemoError("El estado de demo no incluye worker_ids")

        return _validate_worker_ids(
            [str(worker_id).strip() for worker_id in worker_ids if str(worker_id).strip()],
            "worker_ids del estado de demo",
        )

    def _selected_modules_from_state(
        self,
        state: dict[str, Any],
    ) -> tuple[WorkerModuleSpec, ...]:
        return tuple(MODULES_BY_WORKER_ID[worker_id] for worker_id in self._state_worker_ids(state))

    def _load_state(self) -> dict[str, Any]:
        if not self.state_file.exists():
            return {}

        with self.state_file.open("r", encoding="utf-8") as state_reader:
            loaded_state = json.load(state_reader)

        if isinstance(loaded_state, dict):
            return loaded_state

        raise DemoError(f"El estado {self.state_file} debe ser un objeto JSON")

    def _require_state(self, *required_keys: str) -> dict[str, Any]:
        state = self._load_state()
        missing_keys = [key for key in required_keys if key not in state]
        if not missing_keys:
            return state

        missing = ", ".join(missing_keys)
        raise DemoError(
            f"Falta estado de demo ({missing}). Ejecuta antes el paso demo-configure."
        )

    def _save_state(self, state: dict[str, Any]) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        with self.state_file.open("w", encoding="utf-8") as state_writer:
            json.dump(state, state_writer, indent=2, sort_keys=True)
            state_writer.write("\n")

    def _get_or_create_source_connection(self) -> dict[str, Any]:
        name = "Demo ERP/CRM PostgreSQL local"
        existing = self._find_by_name("/api/v1/source-connections", name)
        if existing is not None:
            return existing

        return self._request_json(
            "POST",
            "/api/v1/source-connections",
            {
                "name": name,
                "source_type": "postgresql",
                "host": "postgres",
                "port": 5432,
                "database_name": self.env.get("POSTGRES_DB", "cdc_sync"),
                "credentials": {
                    "user": self.env.get("POSTGRES_USER", "cdc_sync"),
                    "password": self.env.get("POSTGRES_PASSWORD", "cdc_sync"),
                },
            },
        )

    def _get_or_create_destination(self) -> dict[str, Any]:
        name = "Demo ERP/CRM ClickHouse local"
        existing = self._find_by_name("/api/v1/destinations", name)
        if existing is not None:
            return existing

        return self._request_json(
            "POST",
            "/api/v1/destinations",
            {
                "name": name,
                "destination_type": "clickhouse",
                "host": "clickhouse",
                "port": 9000,
                "secure": False,
                "database_name": self.env.get("CLICKHOUSE_DB", "cdc_sync_analytics"),
                "credentials": {
                    "user": self.env.get("CLICKHOUSE_USER", "cdc_sync"),
                    "password": self.env.get("CLICKHOUSE_PASSWORD", "cdc_sync"),
                },
            },
        )

    def _upsert_worker(
        self,
        *,
        module: WorkerModuleSpec,
        existing_worker: dict[str, Any] | None,
        run_id: str,
    ) -> dict[str, Any]:
        payload = {
            "worker_id": module.worker_id,
            "name": f"Demo {module.name}",
            "description": module.description,
            "kafka_group_id": f"cdc-sync-demo-{run_id}-{module.worker_id}",
            "enabled": True,
        }
        if existing_worker is None:
            return self._request_json("POST", "/api/v1/workers", payload)

        return self._request_json(
            "PUT",
            f"/api/v1/workers/{existing_worker['id']}",
            payload,
        )

    def _create_config(
        self,
        *,
        module: WorkerModuleSpec,
        source_connection_id: str,
        destination_id: str,
        run_id: str,
    ) -> dict[str, Any]:
        return self._request_json(
            "POST",
            "/api/v1/configs",
            {
                "name": f"Demo {module.name} {run_id}",
                "source_connection_id": source_connection_id,
                "destination_id": destination_id,
                "sync_mode": "realtime",
                "tables": [_table_payload(table) for table in module.tables],
                "enabled": True,
            },
        )

    def _find_by_name(self, path: str, name: str) -> dict[str, Any] | None:
        for item in self._request_json("GET", path, None):
            if item.get("name") == name:
                return item

        return None

    def _list_by_key(self, path: str, key: str) -> dict[str, dict[str, Any]]:
        items = self._request_json("GET", path, None)
        return {str(item[key]): item for item in items}

    def _request_json(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None,
    ) -> Any:
        data = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request = Request(
            f"{self.api_base_url}{path}",
            data=data,
            headers=headers,
            method=method,
        )
        try:
            with urlopen(request, timeout=15) as response:
                body = response.read().decode("utf-8")
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise DemoError(
                f"La API respondió {exc.code} en {method} {path}: {body}"
            ) from exc
        except URLError as exc:
            raise DemoError(f"No se pudo conectar con la API en {self.api_base_url}") from exc

        if not body:
            return None

        return json.loads(body)

    def _validate_runtime_configs(self, worker_ids: list[str]) -> None:
        for worker_id in worker_ids:
            runtime_config = self._request_json("GET", f"/workers/{worker_id}/config", None)
            worker_payload = (
                runtime_config.get("worker")
                if isinstance(runtime_config, dict)
                else None
            )
            if (
                isinstance(worker_payload, dict)
                and worker_payload.get("worker_id") == worker_id
            ):
                continue

            raise DemoError(
                f"El contrato runtime devuelto no pertenece a '{worker_id}'"
            )

    def _remove_worker_container(
        self,
        container_name: str,
        *,
        report_missing: bool,
    ) -> None:
        if not self._container_exists(container_name):
            if report_missing:
                _print_step(f"El contenedor {container_name} no existe")
            return

        output = _run(["docker", "rm", "-f", container_name], check=False).strip()
        if output and output.splitlines()[-1].strip() == container_name:
            if report_missing:
                _print_step(f"Contenedor eliminado: {container_name}")
            return

        raise DemoError(f"No se pudo eliminar el contenedor {container_name}: {output}")

    def _container_exists(self, container_name: str) -> bool:
        output = _run(
            ["docker", "inspect", "-f", "{{.Id}}", container_name],
            check=False,
        ).strip()
        if output and "no such object" not in output.lower():
            return True

        if "no such object" in output.lower():
            return False

        raise DemoError(f"No se pudo inspeccionar el contenedor {container_name}: {output}")

    def _apply_postgres_demo_schema(self) -> None:
        _print_step("Asegurando esquema ERP/CRM en PostgreSQL local")
        for sql_file in POSTGRES_SCHEMA_FILES:
            sql_path = ROOT_DIR / sql_file
            _run(self._postgres_command(), input_text=sql_path.read_text(encoding="utf-8"))

    def _reset_demo_rows(self) -> None:
        self._postgres_execute(
            """
            BEGIN;
            DELETE FROM sales_payments WHERE payment_reference LIKE 'DEMO-E2E-%';
            DELETE FROM sales_invoices WHERE invoice_number LIKE 'DEMO-E2E-%';
            DELETE FROM sales_order_lines WHERE line_code LIKE 'DEMO-E2E-%';
            DELETE FROM sales_orders WHERE order_number LIKE 'DEMO-E2E-%';
            DELETE FROM crm_activities WHERE activity_code LIKE 'DEMO-E2E-%';
            DELETE FROM crm_opportunities WHERE opportunity_code LIKE 'DEMO-E2E-%';
            DELETE FROM crm_contacts WHERE contact_code LIKE 'DEMO-E2E-%';
            DELETE FROM ops_inventory_movements WHERE movement_code LIKE 'DEMO-E2E-%';
            DELETE FROM ops_products WHERE sku LIKE 'DEMO-E2E-%';
            DELETE FROM ops_warehouses WHERE warehouse_code LIKE 'DEMO-E2E-%';
            DELETE FROM ops_suppliers WHERE supplier_code LIKE 'DEMO-E2E-%';
            DELETE FROM crm_accounts WHERE account_code LIKE 'DEMO-E2E-%';
            COMMIT;
            """
        )

    def _apply_demo_changes(self) -> dict[str, list[str]]:
        deleted: dict[str, list[str]] = {table.name: [] for table in _all_tables()}
        change_summary: list[tuple[str, str, str]] = []

        account_id = self._insert_account("DEMO-E2E-CRM-ACCOUNT-LIVE", "Demo Atlas Corp")
        self._postgres_execute(
            f"UPDATE crm_accounts SET status = 'expanded', annual_revenue = 735000.00 WHERE id = {account_id};"
        )
        deleted_account_id = self._delete_by_unique(
            table="crm_accounts",
            unique_column="account_code",
            unique_value="DEMO-E2E-CRM-ACCOUNT-DELETE",
            insert_sql=(
                "INSERT INTO crm_accounts (account_code, name, segment, status, annual_revenue) "
                "VALUES ('DEMO-E2E-CRM-ACCOUNT-DELETE', 'Demo Account Delete', 'smb', 'inactive', 1000.00) "
                "ON CONFLICT (account_code) DO UPDATE SET name = EXCLUDED.name "
                "RETURNING id::text;"
            ),
        )
        self._record_table_change(
            deleted,
            change_summary,
            "crm_accounts",
            account_id,
            deleted_account_id,
        )

        contact_id = self._insert_contact(
            account_id,
            "DEMO-E2E-CRM-CONTACT-LIVE",
            "demo.crm.contact.live@example.com",
        )
        self._postgres_execute(
            f"UPDATE crm_contacts SET lifecycle_stage = 'champion', role_title = 'IT Director' WHERE id = {contact_id};"
        )
        deleted_contact_id = self._delete_by_unique(
            table="crm_contacts",
            unique_column="contact_code",
            unique_value="DEMO-E2E-CRM-CONTACT-DELETE",
            insert_sql=(
                "INSERT INTO crm_contacts (account_id, contact_code, email, full_name, role_title, lifecycle_stage) "
                f"VALUES ({account_id}, 'DEMO-E2E-CRM-CONTACT-DELETE', 'demo.crm.contact.delete@example.com', "
                "'Demo Contact Delete', 'Analyst', 'lead') "
                "ON CONFLICT (contact_code) DO UPDATE SET full_name = EXCLUDED.full_name "
                "RETURNING id::text;"
            ),
        )
        self._record_table_change(
            deleted,
            change_summary,
            "crm_contacts",
            contact_id,
            deleted_contact_id,
        )

        opportunity_id = self._insert_opportunity(account_id, "DEMO-E2E-CRM-OPP-LIVE")
        self._postgres_execute(
            f"UPDATE crm_opportunities SET stage = 'won', expected_amount = 91000.00 WHERE id = {opportunity_id};"
        )
        deleted_opportunity_id = self._delete_by_unique(
            table="crm_opportunities",
            unique_column="opportunity_code",
            unique_value="DEMO-E2E-CRM-OPP-DELETE",
            insert_sql=(
                "INSERT INTO crm_opportunities (account_id, opportunity_code, title, stage, expected_amount) "
                f"VALUES ({account_id}, 'DEMO-E2E-CRM-OPP-DELETE', 'Demo opportunity delete', 'qualified', 12000.00) "
                "ON CONFLICT (opportunity_code) DO UPDATE SET title = EXCLUDED.title "
                "RETURNING id::text;"
            ),
        )
        self._record_table_change(
            deleted,
            change_summary,
            "crm_opportunities",
            opportunity_id,
            deleted_opportunity_id,
        )

        activity_id = self._insert_activity(account_id, contact_id, "DEMO-E2E-CRM-ACT-LIVE")
        self._postgres_execute(
            f"UPDATE crm_activities SET status = 'completed', subject = 'Demo follow-up completed' WHERE id = {activity_id};"
        )
        deleted_activity_id = self._delete_by_unique(
            table="crm_activities",
            unique_column="activity_code",
            unique_value="DEMO-E2E-CRM-ACT-DELETE",
            insert_sql=(
                "INSERT INTO crm_activities (account_id, contact_id, activity_code, activity_type, subject, status) "
                f"VALUES ({account_id}, {contact_id}, 'DEMO-E2E-CRM-ACT-DELETE', 'email', 'Demo activity delete', 'planned') "
                "ON CONFLICT (activity_code) DO UPDATE SET subject = EXCLUDED.subject "
                "RETURNING id::text;"
            ),
        )
        self._record_table_change(
            deleted,
            change_summary,
            "crm_activities",
            activity_id,
            deleted_activity_id,
        )

        supplier_id = self._insert_supplier("DEMO-E2E-OPS-SUPPLIER-LIVE", "Demo Reliable Supplies")
        self._postgres_execute(
            f"UPDATE ops_suppliers SET status = 'preferred', rating_score = 9.60 WHERE id = {supplier_id};"
        )
        deleted_supplier_id = self._delete_by_unique(
            table="ops_suppliers",
            unique_column="supplier_code",
            unique_value="DEMO-E2E-OPS-SUPPLIER-DELETE",
            insert_sql=(
                "INSERT INTO ops_suppliers (supplier_code, name, status, rating_score) "
                "VALUES ('DEMO-E2E-OPS-SUPPLIER-DELETE', 'Demo Supplier Delete', 'inactive', 4.20) "
                "ON CONFLICT (supplier_code) DO UPDATE SET name = EXCLUDED.name "
                "RETURNING id::text;"
            ),
        )
        self._record_table_change(
            deleted,
            change_summary,
            "ops_suppliers",
            supplier_id,
            deleted_supplier_id,
        )

        product_id = self._insert_product(supplier_id, "DEMO-E2E-OPS-SKU-LIVE")
        self._postgres_execute(
            f"UPDATE ops_products SET status = 'active', unit_cost = 148.90 WHERE id = {product_id};"
        )
        deleted_product_id = self._delete_by_unique(
            table="ops_products",
            unique_column="sku",
            unique_value="DEMO-E2E-OPS-SKU-DELETE",
            insert_sql=(
                "INSERT INTO ops_products (supplier_id, sku, name, category, unit_cost, status) "
                f"VALUES ({supplier_id}, 'DEMO-E2E-OPS-SKU-DELETE', 'Demo Product Delete', 'hardware', 11.00, 'draft') "
                "ON CONFLICT (sku) DO UPDATE SET name = EXCLUDED.name "
                "RETURNING id::text;"
            ),
        )
        self._record_table_change(
            deleted,
            change_summary,
            "ops_products",
            product_id,
            deleted_product_id,
        )

        warehouse_id = self._insert_warehouse("DEMO-E2E-OPS-WH-LIVE", "Demo North Warehouse")
        self._postgres_execute(
            f"UPDATE ops_warehouses SET status = 'active', capacity_units = 9800.00 WHERE id = {warehouse_id};"
        )
        deleted_warehouse_id = self._delete_by_unique(
            table="ops_warehouses",
            unique_column="warehouse_code",
            unique_value="DEMO-E2E-OPS-WH-DELETE",
            insert_sql=(
                "INSERT INTO ops_warehouses (warehouse_code, name, region, capacity_units, status) "
                "VALUES ('DEMO-E2E-OPS-WH-DELETE', 'Demo Warehouse Delete', 'south', 50.00, 'closed') "
                "ON CONFLICT (warehouse_code) DO UPDATE SET name = EXCLUDED.name "
                "RETURNING id::text;"
            ),
        )
        self._record_table_change(
            deleted,
            change_summary,
            "ops_warehouses",
            warehouse_id,
            deleted_warehouse_id,
        )

        movement_id = self._insert_inventory_movement(
            product_id,
            warehouse_id,
            "DEMO-E2E-OPS-MOV-LIVE",
        )
        self._postgres_execute(
            f"UPDATE ops_inventory_movements SET quantity = 44.00, reason = 'quality adjustment' WHERE id = {movement_id};"
        )
        deleted_movement_id = self._delete_by_unique(
            table="ops_inventory_movements",
            unique_column="movement_code",
            unique_value="DEMO-E2E-OPS-MOV-DELETE",
            insert_sql=(
                "INSERT INTO ops_inventory_movements (product_id, warehouse_id, movement_code, movement_type, quantity, reason) "
                f"VALUES ({product_id}, {warehouse_id}, 'DEMO-E2E-OPS-MOV-DELETE', 'outbound', 2.00, 'demo delete') "
                "ON CONFLICT (movement_code) DO UPDATE SET reason = EXCLUDED.reason "
                "RETURNING id::text;"
            ),
        )
        self._record_table_change(
            deleted,
            change_summary,
            "ops_inventory_movements",
            movement_id,
            deleted_movement_id,
        )

        order_id = self._insert_order(account_id, contact_id, "DEMO-E2E-SALES-ORDER-LIVE")
        self._postgres_execute(
            f"UPDATE sales_orders SET status = 'confirmed', total_amount = 624.50 WHERE id = {order_id};"
        )
        deleted_order_id = self._delete_by_unique(
            table="sales_orders",
            unique_column="order_number",
            unique_value="DEMO-E2E-SALES-ORDER-DELETE",
            insert_sql=(
                "INSERT INTO sales_orders (account_id, contact_id, order_number, status, total_amount) "
                f"VALUES ({account_id}, {contact_id}, 'DEMO-E2E-SALES-ORDER-DELETE', 'draft', 99.00) "
                "ON CONFLICT (order_number) DO UPDATE SET status = EXCLUDED.status "
                "RETURNING id::text;"
            ),
        )
        self._record_table_change(
            deleted,
            change_summary,
            "sales_orders",
            order_id,
            deleted_order_id,
        )

        line_id = self._insert_order_line(order_id, product_id, "DEMO-E2E-SALES-LINE-LIVE")
        self._postgres_execute(
            f"UPDATE sales_order_lines SET quantity = 3.00, line_status = 'confirmed' WHERE id = {line_id};"
        )
        deleted_line_id = self._delete_by_unique(
            table="sales_order_lines",
            unique_column="line_code",
            unique_value="DEMO-E2E-SALES-LINE-DELETE",
            insert_sql=(
                "INSERT INTO sales_order_lines (order_id, product_id, line_code, quantity, unit_price, line_status) "
                f"VALUES ({order_id}, {product_id}, 'DEMO-E2E-SALES-LINE-DELETE', 1.00, 12.00, 'draft') "
                "ON CONFLICT (line_code) DO UPDATE SET line_status = EXCLUDED.line_status "
                "RETURNING id::text;"
            ),
        )
        self._record_table_change(
            deleted,
            change_summary,
            "sales_order_lines",
            line_id,
            deleted_line_id,
        )

        invoice_id = self._insert_invoice(order_id, "DEMO-E2E-SALES-INVOICE-LIVE")
        self._postgres_execute(
            f"UPDATE sales_invoices SET status = 'issued', amount_due = 624.50 WHERE id = {invoice_id};"
        )
        deleted_invoice_id = self._delete_by_unique(
            table="sales_invoices",
            unique_column="invoice_number",
            unique_value="DEMO-E2E-SALES-INVOICE-DELETE",
            insert_sql=(
                "INSERT INTO sales_invoices (order_id, invoice_number, status, amount_due) "
                f"VALUES ({order_id}, 'DEMO-E2E-SALES-INVOICE-DELETE', 'draft', 22.00) "
                "ON CONFLICT (invoice_number) DO UPDATE SET status = EXCLUDED.status "
                "RETURNING id::text;"
            ),
        )
        self._record_table_change(
            deleted,
            change_summary,
            "sales_invoices",
            invoice_id,
            deleted_invoice_id,
        )

        payment_id = self._insert_payment(invoice_id, "DEMO-E2E-SALES-PAYMENT-LIVE")
        self._postgres_execute(
            f"UPDATE sales_payments SET status = 'captured', amount_paid = 624.50 WHERE id = {payment_id};"
        )
        deleted_payment_id = self._delete_by_unique(
            table="sales_payments",
            unique_column="payment_reference",
            unique_value="DEMO-E2E-SALES-PAYMENT-DELETE",
            insert_sql=(
                "INSERT INTO sales_payments (invoice_id, payment_reference, status, amount_paid) "
                f"VALUES ({invoice_id}, 'DEMO-E2E-SALES-PAYMENT-DELETE', 'pending', 5.00) "
                "ON CONFLICT (payment_reference) DO UPDATE SET status = EXCLUDED.status "
                "RETURNING id::text;"
            ),
        )
        self._record_table_change(
            deleted,
            change_summary,
            "sales_payments",
            payment_id,
            deleted_payment_id,
        )

        _print_postgres_change_summary(change_summary)
        return deleted

    def _record_table_change(
        self,
        deleted: dict[str, list[str]],
        change_summary: list[tuple[str, str, str]],
        table_name: str,
        live_primary_key: str,
        deleted_primary_key: str,
    ) -> None:
        deleted[table_name].append(deleted_primary_key)
        change_summary.append((table_name, live_primary_key, deleted_primary_key))

    def _insert_account(self, account_code: str, name: str) -> str:
        return self._postgres_scalar(
            "INSERT INTO crm_accounts (account_code, name, segment, status, annual_revenue) "
            f"VALUES ({_sql_literal(account_code)}, {_sql_literal(name)}, 'enterprise', 'active', 710000.00) "
            "ON CONFLICT (account_code) DO UPDATE SET name = EXCLUDED.name "
            "RETURNING id::text;"
        )

    def _insert_contact(self, account_id: str, contact_code: str, email: str) -> str:
        return self._postgres_scalar(
            "INSERT INTO crm_contacts (account_id, contact_code, email, full_name, role_title, lifecycle_stage) "
            f"VALUES ({account_id}, {_sql_literal(contact_code)}, {_sql_literal(email)}, 'Demo CRM Contact', 'Manager', 'lead') "
            "ON CONFLICT (contact_code) DO UPDATE SET email = EXCLUDED.email "
            "RETURNING id::text;"
        )

    def _insert_opportunity(self, account_id: str, opportunity_code: str) -> str:
        return self._postgres_scalar(
            "INSERT INTO crm_opportunities (account_id, opportunity_code, title, stage, expected_amount) "
            f"VALUES ({account_id}, {_sql_literal(opportunity_code)}, 'Demo ERP expansion', 'proposal', 88000.00) "
            "ON CONFLICT (opportunity_code) DO UPDATE SET title = EXCLUDED.title "
            "RETURNING id::text;"
        )

    def _insert_activity(self, account_id: str, contact_id: str, activity_code: str) -> str:
        return self._postgres_scalar(
            "INSERT INTO crm_activities (account_id, contact_id, activity_code, activity_type, subject, status) "
            f"VALUES ({account_id}, {contact_id}, {_sql_literal(activity_code)}, 'meeting', 'Demo follow-up', 'planned') "
            "ON CONFLICT (activity_code) DO UPDATE SET subject = EXCLUDED.subject "
            "RETURNING id::text;"
        )

    def _insert_supplier(self, supplier_code: str, name: str) -> str:
        return self._postgres_scalar(
            "INSERT INTO ops_suppliers (supplier_code, name, status, rating_score) "
            f"VALUES ({_sql_literal(supplier_code)}, {_sql_literal(name)}, 'active', 8.90) "
            "ON CONFLICT (supplier_code) DO UPDATE SET name = EXCLUDED.name "
            "RETURNING id::text;"
        )

    def _insert_product(self, supplier_id: str, sku: str) -> str:
        return self._postgres_scalar(
            "INSERT INTO ops_products (supplier_id, sku, name, category, unit_cost, status) "
            f"VALUES ({supplier_id}, {_sql_literal(sku)}, 'Demo Scanner', 'hardware', 151.25, 'draft') "
            "ON CONFLICT (sku) DO UPDATE SET name = EXCLUDED.name "
            "RETURNING id::text;"
        )

    def _insert_warehouse(self, warehouse_code: str, name: str) -> str:
        return self._postgres_scalar(
            "INSERT INTO ops_warehouses (warehouse_code, name, region, capacity_units, status) "
            f"VALUES ({_sql_literal(warehouse_code)}, {_sql_literal(name)}, 'north', 9400.00, 'opening') "
            "ON CONFLICT (warehouse_code) DO UPDATE SET name = EXCLUDED.name "
            "RETURNING id::text;"
        )

    def _insert_inventory_movement(
        self,
        product_id: str,
        warehouse_id: str,
        movement_code: str,
    ) -> str:
        return self._postgres_scalar(
            "INSERT INTO ops_inventory_movements (product_id, warehouse_id, movement_code, movement_type, quantity, reason) "
            f"VALUES ({product_id}, {warehouse_id}, {_sql_literal(movement_code)}, 'inbound', 40.00, 'demo inbound') "
            "ON CONFLICT (movement_code) DO UPDATE SET reason = EXCLUDED.reason "
            "RETURNING id::text;"
        )

    def _insert_order(self, account_id: str, contact_id: str, order_number: str) -> str:
        return self._postgres_scalar(
            "INSERT INTO sales_orders (account_id, contact_id, order_number, status, total_amount) "
            f"VALUES ({account_id}, {contact_id}, {_sql_literal(order_number)}, 'draft', 453.75) "
            "ON CONFLICT (order_number) DO UPDATE SET status = EXCLUDED.status "
            "RETURNING id::text;"
        )

    def _insert_order_line(self, order_id: str, product_id: str, line_code: str) -> str:
        return self._postgres_scalar(
            "INSERT INTO sales_order_lines (order_id, product_id, line_code, quantity, unit_price, line_status) "
            f"VALUES ({order_id}, {product_id}, {_sql_literal(line_code)}, 2.00, 151.25, 'draft') "
            "ON CONFLICT (line_code) DO UPDATE SET line_status = EXCLUDED.line_status "
            "RETURNING id::text;"
        )

    def _insert_invoice(self, order_id: str, invoice_number: str) -> str:
        return self._postgres_scalar(
            "INSERT INTO sales_invoices (order_id, invoice_number, status, amount_due) "
            f"VALUES ({order_id}, {_sql_literal(invoice_number)}, 'draft', 453.75) "
            "ON CONFLICT (invoice_number) DO UPDATE SET status = EXCLUDED.status "
            "RETURNING id::text;"
        )

    def _insert_payment(self, invoice_id: str, payment_reference: str) -> str:
        return self._postgres_scalar(
            "INSERT INTO sales_payments (invoice_id, payment_reference, status, amount_paid) "
            f"VALUES ({invoice_id}, {_sql_literal(payment_reference)}, 'pending', 100.00) "
            "ON CONFLICT (payment_reference) DO UPDATE SET status = EXCLUDED.status "
            "RETURNING id::text;"
        )

    def _delete_by_unique(
        self,
        *,
        table: str,
        unique_column: str,
        unique_value: str,
        insert_sql: str,
    ) -> str:
        self._postgres_scalar(insert_sql)
        deleted_id = self._postgres_scalar(
            f"DELETE FROM {table} WHERE {unique_column} = {_sql_literal(unique_value)} RETURNING id::text;"
        )
        if deleted_id:
            return deleted_id

        raise DemoError(f"No se pudo borrar la fila de demo en {table}")

    def _assert_live_rows(self, state: dict[str, Any]) -> dict[str, int]:
        live_row_counts: dict[str, int] = {}
        for table in self._selected_tables_from_state(state):
            expected_rows = [
                _normalize_row(table, row)
                for row in self._postgres_table_rows(table)
            ]
            actual_rows = [
                _normalize_row(table, row)
                for row in self._clickhouse_live_rows(table)
            ]
            _assert_rows_match(table, expected_rows, actual_rows)
            live_row_counts[table.name] = len(expected_rows)

        return live_row_counts

    def _assert_deleted_tombstones(self, state: dict[str, Any]) -> dict[str, int]:
        deleted_primary_keys = state.get("deleted_primary_keys")
        if not isinstance(deleted_primary_keys, dict):
            raise DemoError("El estado de demo no incluye deleted_primary_keys")

        tombstone_counts: dict[str, int] = {}
        for table in self._selected_tables_from_state(state):
            expected_keys = {
                (int(primary_key),)
                for primary_key in deleted_primary_keys.get(table.name, [])
            }
            if not expected_keys:
                raise ReconciliationError(
                    f"No hay claves borradas registradas para {table.name}"
                )

            actual_keys = {
                _row_key(table, _normalize_row(table, row))
                for row in self._clickhouse_deleted_rows(table)
            }
            missing_keys = expected_keys - actual_keys
            if not missing_keys:
                tombstone_counts[table.name] = len(expected_keys)
                continue

            raise ReconciliationError(
                f"Faltan lápidas deleted=1 en {table.name}: {sorted(missing_keys)}"
            )

        return tombstone_counts

    def _selected_tables_from_state(self, state: dict[str, Any]) -> tuple[TableSpec, ...]:
        tables: list[TableSpec] = []
        for module in self._selected_modules_from_state(state):
            tables.extend(module.tables)

        return tuple(tables)

    def _postgres_table_rows(self, table: TableSpec) -> list[dict[str, Any]]:
        columns = ", ".join(
            f"{_quote_postgres_identifier(column.name)}::text AS {_quote_postgres_identifier(column.name)}"
            for column in table.columns
        )
        query = (
            "SELECT COALESCE(json_agg(row_to_json(source_row)), '[]'::json) "
            f"FROM (SELECT {columns} FROM public.{_quote_postgres_identifier(table.name)} ORDER BY id) AS source_row;"
        )
        raw_rows = self._postgres_scalar(query)
        loaded_rows = json.loads(raw_rows)
        if isinstance(loaded_rows, list):
            return loaded_rows

        raise DemoError(f"La consulta PostgreSQL de {table.name} no devolvió una lista")

    def _clickhouse_live_rows(self, table: TableSpec) -> list[dict[str, Any]]:
        return self._clickhouse_table_rows(table, deleted=False)

    def _clickhouse_deleted_rows(self, table: TableSpec) -> list[dict[str, Any]]:
        return self._clickhouse_table_rows(table, deleted=True)

    def _clickhouse_table_rows(
        self,
        table: TableSpec,
        *,
        deleted: bool,
    ) -> list[dict[str, Any]]:
        columns = ", ".join(
            (
                f"if(isNull({_quote_clickhouse_identifier(column.name)}), NULL, "
                f"toString({_quote_clickhouse_identifier(column.name)})) AS "
                f"{_quote_clickhouse_identifier(column.name)}"
            )
            for column in table.columns
        )
        deleted_value = 1 if deleted else 0
        query = (
            f"SELECT {columns} "
            f"FROM {_quote_clickhouse_identifier(self.env.get('CLICKHOUSE_DB', 'cdc_sync_analytics'))}."
            f"{_quote_clickhouse_identifier(table.name)} FINAL "
            f"WHERE deleted = {deleted_value} FORMAT JSONEachRow"
        )
        output = self._clickhouse_query(query)
        rows = []
        for line in output.splitlines():
            if line.strip():
                rows.append(json.loads(line))

        return rows

    def _postgres_command(self) -> list[str]:
        return [
            "docker",
            "compose",
            "exec",
            "-T",
            "postgres",
            "psql",
            "-v",
            "ON_ERROR_STOP=1",
            "-U",
            self.env.get("POSTGRES_USER", "cdc_sync"),
            "-d",
            self.env.get("POSTGRES_DB", "cdc_sync"),
        ]

    def _postgres_execute(self, sql: str) -> str:
        return _run(self._postgres_command(), input_text=sql)

    def _postgres_scalar(self, sql: str) -> str:
        command = self._postgres_command() + ["-qAt", "-c", sql]
        return _run(command).strip()

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

    def _wait_for_api(self) -> None:
        _wait_until(
            "API REST",
            lambda: self._http_get(f"{self.api_base_url}/health"),
        )

    def _wait_for_connect(self) -> None:
        _wait_until(
            "Kafka Connect",
            lambda: self._http_get(f"{self.connect_base_url}/"),
        )

    def _wait_for_postgres(self) -> None:
        _wait_until(
            "PostgreSQL OLTP",
            lambda: self._postgres_scalar("SELECT 1;") == "1",
        )

    def _wait_for_control_plane_postgres(self) -> None:
        _wait_until(
            "PostgreSQL del control plane",
            lambda: _run(
                [
                    "docker",
                    "compose",
                    "exec",
                    "-T",
                    "control-plane-postgres",
                    "pg_isready",
                    "-U",
                    self.env.get("CONTROL_PLANE_POSTGRES_USER", "cdc_sync_control_plane"),
                    "-d",
                    self.env.get("CONTROL_PLANE_POSTGRES_DB", "cdc_sync_control_plane"),
                ]
            )
            is not None,
        )

    def _wait_for_kafka(self) -> None:
        _wait_until(
            "Kafka",
            lambda: _run(
                [
                    "docker",
                    "compose",
                    "exec",
                    "-T",
                    "kafka",
                    "kafka-topics",
                    "--bootstrap-server",
                    "kafka:29092",
                    "--list",
                ]
            )
            is not None,
        )

    def _wait_for_clickhouse(self) -> None:
        _wait_until(
            "ClickHouse",
            lambda: self._clickhouse_query("SELECT 1").strip() == "1",
        )

    def _wait_for_connector(self, connector_name: str) -> None:
        def connector_is_running() -> bool:
            status = self._http_get(
                f"{self.connect_base_url}/connectors/{connector_name}/status"
            )
            connector = status.get("connector", {})
            tasks = status.get("tasks", [])
            return (
                connector.get("state") == "RUNNING"
                and bool(tasks)
                and all(task.get("state") == "RUNNING" for task in tasks)
            )

        _wait_until(f"conector {connector_name}", connector_is_running, attempts=30)

    def _wait_for_container_running(self, container_name: str) -> None:
        def container_is_running() -> bool:
            output = _run(
                [
                    "docker",
                    "inspect",
                    "-f",
                    "{{.State.Running}}",
                    container_name,
                ],
                check=False,
            )
            return output.strip() == "true"

        _wait_until(f"contenedor {container_name}", container_is_running, attempts=10)

    def _http_get(self, url: str) -> Any:
        try:
            with urlopen(url, timeout=10) as response:
                body = response.read().decode("utf-8")
        except (HTTPError, URLError) as exc:
            raise DemoError(f"No se pudo consultar {url}") from exc

        if not body:
            return {}

        return json.loads(body)

    def _diagnostics(self, state: dict[str, Any]) -> str:
        sections = [
            ("docker compose ps", _run(["docker", "compose", "ps"], check=False)),
        ]
        connector_name = state.get("connector_name")
        if isinstance(connector_name, str):
            try:
                connector_status = json.dumps(
                    self._http_get(f"{self.connect_base_url}/connectors/{connector_name}/status"),
                    indent=2,
                    sort_keys=True,
                )
            except DemoError as exc:
                connector_status = str(exc)
            sections.append((f"Estado del conector {connector_name}", connector_status))

        worker_containers = state.get("worker_containers", {})
        if isinstance(worker_containers, dict):
            for worker_id, container_name in worker_containers.items():
                logs = _run(["docker", "logs", "--tail", "80", str(container_name)], check=False)
                sections.append((f"Logs de {worker_id}", logs))

        return "\n\n".join(f"== {title} ==\n{content}" for title, content in sections)


def _table_payload(table: TableSpec) -> dict[str, Any]:
    return {
        "logical_name": table.name,
        "source_schema": "public",
        "source_table": table.name,
        "cdc_topic": table.topic,
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


def _all_tables() -> tuple[TableSpec, ...]:
    tables: list[TableSpec] = []
    for module in MODULES_BY_WORKER_ID.values():
        tables.extend(module.tables)

    return tuple(tables)


def _normalize_row(table: TableSpec, raw_row: dict[str, Any]) -> dict[str, Any]:
    normalized_row: dict[str, Any] = {}
    for column in table.columns:
        raw_value = raw_row.get(column.name)
        if raw_value is None:
            if column.nullable:
                normalized_row[column.name] = None
                continue

            raise ReconciliationError(
                f"{table.name}.{column.name} no puede ser null en la reconciliación"
            )

        normalized_row[column.name] = _normalize_value(column, raw_value)

    return normalized_row


def _normalize_value(column: ColumnSpec, raw_value: Any) -> Any:
    if column.value_kind == UINT:
        return int(raw_value)

    if column.value_kind == DECIMAL:
        return Decimal(str(raw_value))

    if column.value_kind == TEXT:
        return str(raw_value)

    raise DemoError(f"Tipo de valor no soportado: {column.value_kind}")


def _assert_rows_match(
    table: TableSpec,
    expected_rows: list[dict[str, Any]],
    actual_rows: list[dict[str, Any]],
) -> None:
    expected_by_key = {_row_key(table, row): row for row in expected_rows}
    actual_by_key = {_row_key(table, row): row for row in actual_rows}

    missing_keys = sorted(set(expected_by_key) - set(actual_by_key))
    extra_keys = sorted(set(actual_by_key) - set(expected_by_key))
    changed_rows = [
        {
            "pk": key,
            "expected": _jsonable_row(expected_by_key[key]),
            "actual": _jsonable_row(actual_by_key[key]),
        }
        for key in sorted(set(expected_by_key) & set(actual_by_key))
        if expected_by_key[key] != actual_by_key[key]
    ]
    if not missing_keys and not extra_keys and not changed_rows:
        return

    raise ReconciliationError(
        f"Diferencias en {table.name}: "
        f"faltan={missing_keys[:10]} "
        f"sobran={extra_keys[:10]} "
        f"cambios={json.dumps(changed_rows[:5], ensure_ascii=False)}"
    )


def _row_key(table: TableSpec, row: dict[str, Any]) -> tuple[Any, ...]:
    return tuple(row[column_name] for column_name in table.primary_key)


def _jsonable_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        key: str(value) if isinstance(value, Decimal) else value
        for key, value in row.items()
    }


def _quote_postgres_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _quote_clickhouse_identifier(identifier: str) -> str:
    return "`" + identifier.replace("`", "``") + "`"


def _sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _container_name(worker_id: str) -> str:
    return f"cdc-sync-demo-worker-{worker_id}"


def _parse_worker_ids(raw_worker_ids: str | None, variable_name: str) -> list[str]:
    if raw_worker_ids is None:
        raise DemoError(f"{variable_name} debe incluir al menos un worker")

    worker_ids = [
        worker_id.strip()
        for worker_id in raw_worker_ids.split(",")
        if worker_id.strip()
    ]
    return _validate_worker_ids(worker_ids, variable_name)


def _validate_worker_ids(worker_ids: list[str], variable_name: str) -> list[str]:
    if not worker_ids:
        raise DemoError(f"{variable_name} debe incluir al menos un worker")

    duplicated_worker_ids = {
        worker_id for worker_id in worker_ids if worker_ids.count(worker_id) > 1
    }
    if duplicated_worker_ids:
        duplicated = ", ".join(sorted(duplicated_worker_ids))
        raise DemoError(f"{variable_name} contiene workers duplicados: {duplicated}")

    invalid_worker_ids = [
        worker_id
        for worker_id in worker_ids
        if WORKER_ID_PATTERN.fullmatch(worker_id) is None
    ]
    if invalid_worker_ids:
        invalid = ", ".join(invalid_worker_ids)
        raise DemoError(
            f"{variable_name} contiene workers no válidos para nombres de "
            f"contenedor estables: {invalid}"
        )

    return worker_ids


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
        "DEMO_WORKER_IDS": DEFAULT_WORKER_IDS,
        "DEMO_STATE_FILE": DEFAULT_STATE_FILE,
    }
    env.update(_read_dotenv(ROOT_DIR / ".env"))
    env.update({key: value for key, value in os.environ.items() if value is not None})
    return env


def _read_dotenv(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        normalized_value = value.strip()
        if (
            len(normalized_value) >= 2
            and normalized_value[0] == normalized_value[-1]
            and normalized_value[0] in {"'", '"'}
        ):
            normalized_value = normalized_value[1:-1]

        values[key.strip()] = normalized_value

    return values


def _run(
    command: list[str],
    *,
    input_text: str | None = None,
    check: bool = True,
) -> str:
    result = subprocess.run(
        command,
        input=input_text,
        cwd=ROOT_DIR,
        text=True,
        capture_output=True,
        check=False,
    )
    if check and result.returncode != 0:
        command_text = " ".join(command)
        raise DemoError(
            f"Falló el comando: {command_text}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )

    if result.returncode != 0:
        return result.stdout + result.stderr

    return result.stdout


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

    raise DemoError(f"{label} no está listo. Último error: {last_error}")


def _print_step(message: str) -> None:
    print(f"[demo] {message}", flush=True)


def _print_ok(message: str) -> None:
    print(f"[demo] OK: {message}", flush=True)


def _print_postgres_change_summary(
    change_summary: list[tuple[str, str, str]],
) -> None:
    print("[demo] PostgreSQL: cambios aplicados y claves esperadas")
    for table_name, live_primary_key, deleted_primary_key in change_summary:
        print(
            "[demo]   "
            f"{table_name}: fila viva id={live_primary_key}; "
            f"lápida esperada id={deleted_primary_key}"
        )


def _print_reconciliation_summary(
    live_row_counts: dict[str, int],
    tombstone_counts: dict[str, int],
) -> None:
    print("[demo] ClickHouse FINAL: estado reconciliado")
    for table_name, live_count in live_row_counts.items():
        tombstone_count = tombstone_counts.get(table_name, 0)
        print(
            "[demo]   "
            f"{table_name}: filas_vivas={live_count}; deletes_lógicos={tombstone_count}"
        )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Demo local multi-worker ERP/CRM desde configuración API.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in (
        "up",
        "migrate",
        "configure",
        "materialize",
        "workers",
        "changes",
        "assert",
        "all",
    ):
        subparsers.add_parser(command)

    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    runner = DemoRunner()
    commands = {
        "up": runner.up,
        "migrate": runner.migrate,
        "configure": runner.configure,
        "materialize": runner.materialize,
        "workers": runner.workers,
        "changes": runner.changes,
        "assert": runner.assert_state,
        "all": runner.all,
    }

    try:
        commands[args.command]()
        return 0
    except DemoError as exc:
        print(f"[demo] ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

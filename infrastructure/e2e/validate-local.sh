#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="$ROOT_DIR/.env"
WORKER_TABLE_CONFIG_FILE="$ROOT_DIR/worker/config/tables.json"
E2E_TABLE_CONFIG_PATH="config/tables.e2e.json"
E2E_TABLE_CONFIG_FILE="$ROOT_DIR/worker/config/tables.e2e.json"
CONNECTOR_ENV_FILE="$ROOT_DIR/infrastructure/debezium/connectors/generated/postgresql-source.local.env"
E2E_CLICKHOUSE_DB_PREFIX="cdc_sync_analytics_e2e"
CONNECTOR_CONFIG_FILE="$ROOT_DIR/infrastructure/debezium/connectors/generated/postgresql-source.local.json"
POLL_INTERVAL_SECONDS="${E2E_POLL_INTERVAL_SECONDS:-2}"
PHASE_TIMEOUT_SECONDS="${E2E_TIMEOUT_SECONDS:-120}"
CONNECT_RETRY_ATTEMPTS="${CONNECT_RETRY_ATTEMPTS:-15}"
CONNECT_RETRY_DELAY_SECONDS="${CONNECT_RETRY_DELAY_SECONDS:-2}"
E2E_VERBOSE="${E2E_VERBOSE:-0}"
GENERATED_E2E_TABLE_CONFIG=0

log() {
  printf '[e2e] %s\n' "$*"
}

prefix_block() {
  sed 's/^/[e2e]   /'
}

log_block() {
  local title="$1"
  local body="$2"

  log "$title"
  printf '%s\n' "$body" | prefix_block
}

is_verbose() {
  [[ "$E2E_VERBOSE" == "1" ]]
}

fail() {
  printf '[e2e] ERROR: %s\n' "$*" >&2
  exit 1
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    fail "Falta el comando requerido '$1'"
  fi
}

ensure_e2e_table_config() {
  if [[ -f "$E2E_TABLE_CONFIG_FILE" ]]; then
    return 0
  fi

  log "Generando configuración e2e del worker en $E2E_TABLE_CONFIG_FILE"
  mkdir -p "$(dirname "$E2E_TABLE_CONFIG_FILE")"
  cat >"$E2E_TABLE_CONFIG_FILE" <<'EOF'
{
  "version": 2,
  "tables": {
    "customers": {
      "enabled": true,
      "source": {
        "adapter": "debezium_postgres",
        "connection": "postgres_local",
        "schema": "public",
        "table": "customers",
        "topic": "cdc_sync.public.customers"
      },
      "pk": ["id"],
      "sync": {
        "mode": "realtime"
      },
      "destination": {
        "table": "customers",
        "default_nullable": true,
        "columns": [
          { "name": "id", "type": "UInt64", "nullable": false },
          { "name": "email", "type": "String" },
          { "name": "full_name", "type": "String" },
          { "name": "created_at", "type": "DateTime64(3, 'UTC')", "nullable": true }
        ]
      }
    },
    "orders": {
      "enabled": true,
      "source": {
        "adapter": "debezium_postgres",
        "connection": "postgres_local",
        "schema": "public",
        "table": "orders",
        "topic": "cdc_sync.public.orders"
      },
      "pk": ["id"],
      "sync": {
        "mode": "realtime"
      },
      "destination": {
        "table": "orders",
        "default_nullable": true,
        "columns": [
          { "name": "id", "type": "UInt64", "nullable": false },
          { "name": "customer_id", "type": "UInt64" },
          { "name": "order_number", "type": "String" },
          { "name": "total_amount", "type": "Decimal(10, 2)" },
          { "name": "status", "type": "String", "nullable": false },
          { "name": "created_at", "type": "DateTime64(3, 'UTC')" }
        ]
      }
    }
  }
}
EOF
  GENERATED_E2E_TABLE_CONFIG=1
}

cleanup_generated_e2e_table_config() {
  if (( GENERATED_E2E_TABLE_CONFIG == 1 )) && [[ -f "$E2E_TABLE_CONFIG_FILE" ]]; then
    rm -f "$E2E_TABLE_CONFIG_FILE"
  fi
}

compose() {
  docker compose --project-directory "$ROOT_DIR" -f "$ROOT_DIR/docker-compose.yml" "$@"
}

postgres_query() {
  local query="$1"

  compose exec -T postgres \
    psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -tA -c "$query"
}

clickhouse_query() {
  local query="$1"

  compose exec -T clickhouse \
    clickhouse-client \
    --user "$CLICKHOUSE_USER" \
    --password "$CLICKHOUSE_PASSWORD" \
    --query "$query"
}

trim_output() {
  printf '%s' "$1" | sed -e 's/[[:space:]]\+$//'
}

pretty_print_json() {
  local raw_json="$1"

  python3 -c '
import json
import sys

raw = sys.stdin.read().strip()
if not raw:
    raise SystemExit(0)

try:
    parsed = json.loads(raw)
except json.JSONDecodeError:
    lines = [line for line in raw.splitlines() if line.strip()]
    try:
        parsed = [json.loads(line) for line in lines]
    except json.JSONDecodeError:
        print(raw)
        raise SystemExit(0)

print(json.dumps(parsed, indent=2, ensure_ascii=False, sort_keys=True))
' <<<"$raw_json"
}

redact_json() {
  local raw_json="$1"

  python3 -c '
import json
import sys

def redact(value):
    if isinstance(value, dict):
        redacted = {}
        for key, nested_value in value.items():
            if "password" in key.lower():
                redacted[key] = "***"
            else:
                redacted[key] = redact(nested_value)
        return redacted
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value

raw = sys.stdin.read().strip()
if not raw:
    raise SystemExit(0)

try:
    parsed = json.loads(raw)
except json.JSONDecodeError:
    print(raw)
    raise SystemExit(0)

print(json.dumps(redact(parsed), ensure_ascii=False))
' <<<"$raw_json"
}

json_from_pairs() {
  python3 - "$@" <<'PY'
import json
import sys

args = sys.argv[1:]
if len(args) % 2 != 0:
    raise SystemExit("Se esperaban pares clave/valor")

payload = {}
for index in range(0, len(args), 2):
    payload[args[index]] = args[index + 1]

print(json.dumps(payload, ensure_ascii=False))
PY
}

log_json_pairs() {
  local title="$1"
  shift

  local payload
  payload="$(json_from_pairs "$@")"
  log_block "$title" "$(pretty_print_json "$payload")"
}

log_pretty_json() {
  local title="$1"
  local raw_json="$2"

  if [[ -z "$raw_json" ]]; then
    return 0
  fi

  log_block "$title" "$(pretty_print_json "$raw_json")"
}

log_verbose_pretty_json() {
  local title="$1"
  local raw_json="$2"

  if ! is_verbose; then
    return 0
  fi

  log_pretty_json "$title" "$raw_json"
}

extract_json_data_section() {
  local raw_json="$1"

  python3 -c '
import json
import sys

raw = sys.stdin.read().strip()
if not raw:
    raise SystemExit(0)

parsed = json.loads(raw)
payload = parsed.get("data", parsed)
print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
' <<<"$raw_json"
}

summarize_compose_services_json() {
  local raw_json="$1"

  python3 -c '
import json
import sys

raw = sys.stdin.read().strip()
if not raw:
    raise SystemExit(0)

try:
    parsed = json.loads(raw)
except json.JSONDecodeError:
    parsed = [json.loads(line) for line in raw.splitlines() if line.strip()]

summary = []
for item in parsed:
    summary.append(
        {
            "service": item.get("Service"),
            "state": item.get("State"),
            "health": item.get("Health"),
            "status": item.get("Status"),
        }
    )

print(json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True))
' <<<"$raw_json"
}

log_clickhouse_json_query() {
  local title="$1"
  local query="$2"
  local result=""

  result="$(clickhouse_query "$query")"
  if is_verbose; then
    log_pretty_json "$title" "$result"
    return 0
  fi

  log_block "$title" "$(extract_json_data_section "$result")"
}

compose_up() {
  if is_verbose; then
    compose up -d --build
    return 0
  fi

  compose up -d --build >/dev/null
}

wait_for_postgres_ready() {
  local deadline=$((SECONDS + PHASE_TIMEOUT_SECONDS))

  while (( SECONDS < deadline )); do
    if postgres_query "SELECT 1;" >/dev/null 2>&1; then
      log_json_pairs \
        "PostgreSQL listo" \
        "database" "$POSTGRES_DB" \
        "user" "$POSTGRES_USER"
      return 0
    fi

    sleep "$POLL_INTERVAL_SECONDS"
  done

  fail "Fallo en fase 'arranque': PostgreSQL no responde dentro del timeout"
}

render_connector_config() {
  log "Renderizando configuración de Debezium"
  make -C "$ROOT_DIR" debezium-postgres-render >/dev/null

  if [[ ! -f "$CONNECTOR_CONFIG_FILE" ]]; then
    fail "Fallo en fase 'conector': no se ha generado $CONNECTOR_CONFIG_FILE"
  fi

  local rendered_config=""
  rendered_config="$(<"$CONNECTOR_CONFIG_FILE")"
  log_verbose_pretty_json \
    "Configuración Debezium renderizada (secretos ocultos)" \
    "$(redact_json "$rendered_config")"
}

apply_connector_config() {
  local attempt=1
  local response_file=""
  local error_file=""
  local response_body=""
  local error_body=""
  local http_status=""
  local curl_exit_code=0
  local last_error=""

  while (( attempt <= CONNECT_RETRY_ATTEMPTS )); do
    response_file="$(mktemp)"
    error_file="$(mktemp)"

    set +e
    http_status="$(
      curl --silent --show-error \
        --output "$response_file" \
        --write-out "%{http_code}" \
        -X PUT \
        "http://localhost:${CONNECT_PORT}/connectors/${DEBEZIUM_POSTGRES_CONNECTOR_NAME}/config" \
        -H "Content-Type: application/json" \
        --data @"$CONNECTOR_CONFIG_FILE" \
        2>"$error_file"
    )"
    curl_exit_code=$?
    set -e

    response_body="$(cat "$response_file")"
    error_body="$(trim_output "$(cat "$error_file")")"
    rm -f "$response_file" "$error_file"

    if (( curl_exit_code == 0 )) && [[ "$http_status" =~ ^2 ]]; then
      log_json_pairs \
        "Conector Debezium aplicado" \
        "connector" "$DEBEZIUM_POSTGRES_CONNECTOR_NAME" \
        "attempt" "$attempt" \
        "http_status" "$http_status"
      log_verbose_pretty_json \
        "Respuesta de Kafka Connect al aplicar el conector" \
        "$(redact_json "$response_body")"
      return 0
    fi

    last_error="${error_body:-HTTP ${http_status:-000}}"
    log_json_pairs \
      "Reintento al aplicar el conector" \
      "connector" "$DEBEZIUM_POSTGRES_CONNECTOR_NAME" \
      "attempt" "$attempt" \
      "curl_exit_code" "$curl_exit_code" \
      "http_status" "${http_status:-000}" \
      "error" "$last_error"

    if (( attempt < CONNECT_RETRY_ATTEMPTS )); then
      sleep "$CONNECT_RETRY_DELAY_SECONDS"
    fi

    ((attempt++))
  done

  fail "Fallo en fase 'conector': no se pudo aplicar el conector '${DEBEZIUM_POSTGRES_CONNECTOR_NAME}'. Último error: ${last_error}"
}

wait_for_connector_running() {
  local deadline=$((SECONDS + PHASE_TIMEOUT_SECONDS))
  local status_json=""
  local normalized_status=""
  local running_states=""

  while (( SECONDS < deadline )); do
    if status_json="$(curl -fsS "http://localhost:${CONNECT_PORT}/connectors/${DEBEZIUM_POSTGRES_CONNECTOR_NAME}/status" 2>/dev/null)"; then
      normalized_status="$(printf '%s' "$status_json" | tr -d '[:space:]')"

      if [[ "$normalized_status" == *'"state":"FAILED"'* ]]; then
        log_pretty_json "Estado fallido del conector" "$status_json"
        fail "Fallo en fase 'conector': Kafka Connect devuelve estado FAILED"
      fi

      running_states="$(printf '%s' "$normalized_status" | grep -o '"state":"RUNNING"' || true)"
      if [[ -n "$running_states" && "$(printf '%s\n' "$running_states" | wc -l | tr -d ' ')" -ge 2 ]]; then
        if is_verbose; then
          log_pretty_json "Estado final del conector" "$status_json"
        else
          log_json_pairs \
            "Estado final del conector" \
            "name" "$DEBEZIUM_POSTGRES_CONNECTOR_NAME" \
            "connector_state" "RUNNING" \
            "tasks_running" "1"
        fi
        return 0
      fi
    fi

    sleep "$POLL_INTERVAL_SECONDS"
  done

  if [[ -n "$status_json" ]]; then
    log_pretty_json "Último estado observado del conector" "$status_json"
  fi
  fail "Fallo en fase 'conector': el conector '${DEBEZIUM_POSTGRES_CONNECTOR_NAME}' no alcanza RUNNING"
}

wait_for_clickhouse_tables() {
  local deadline=$((SECONDS + PHASE_TIMEOUT_SECONDS))
  local customers_ready=""
  local orders_ready=""

  while (( SECONDS < deadline )); do
    customers_ready="$(clickhouse_query "EXISTS TABLE ${WORKER_CLICKHOUSE_DB}.customers" 2>/dev/null | tr -d '[:space:]' || true)"
    orders_ready="$(clickhouse_query "EXISTS TABLE ${WORKER_CLICKHOUSE_DB}.orders" 2>/dev/null | tr -d '[:space:]' || true)"

    if [[ "$customers_ready" == "1" && "$orders_ready" == "1" ]]; then
      log_clickhouse_json_query \
        "Tablas ClickHouse preparadas" \
        "SELECT name FROM system.tables WHERE database = '${WORKER_CLICKHOUSE_DB}' AND name IN ('customers', 'orders') ORDER BY name FORMAT JSON"
      return 0
    fi

    sleep "$POLL_INTERVAL_SECONDS"
  done

  fail "Fallo en fase 'arranque': ClickHouse no expone las tablas esperadas 'customers' y 'orders'"
}

wait_for_clickhouse_result() {
  local phase="$1"
  local query="$2"
  local expected="$3"
  local deadline=$((SECONDS + PHASE_TIMEOUT_SECONDS))
  local result=""

  while (( SECONDS < deadline )); do
    if result="$(clickhouse_query "$query" 2>/dev/null)"; then
      result="$(trim_output "$result")"
      if [[ "$result" == "$expected" ]]; then
        return 0
      fi
    fi

    sleep "$POLL_INTERVAL_SECONDS"
  done

  fail "Fallo en fase '${phase}': resultado inesperado en ClickHouse. Esperado [$expected]. Obtenido [${result:-<sin resultado>}]"
}

wait_for_clickhouse_number_greater_than() {
  local phase="$1"
  local query="$2"
  local threshold="$3"
  local deadline=$((SECONDS + PHASE_TIMEOUT_SECONDS))
  local result=""

  while (( SECONDS < deadline )); do
    if result="$(clickhouse_query "$query" 2>/dev/null | tr -d '[:space:]')"; then
      if [[ "$result" =~ ^[0-9]+$ ]] && (( result > threshold )); then
        return 0
      fi
    fi

    sleep "$POLL_INTERVAL_SECONDS"
  done

  fail "Fallo en fase '${phase}': se esperaba una version mayor que ${threshold} y se obtuvo [${result:-<sin resultado>}]"
}

log_compose_services() {
  local services_json=""

  services_json="$(compose ps --format json)"
  if is_verbose; then
    log_pretty_json "Estado de servicios Docker" "$services_json"
    return 0
  fi

  log_block "Estado de servicios Docker" "$(summarize_compose_services_json "$services_json")"
}

prepare_local_environment() {
  ensure_e2e_table_config

  if [[ -f "$ENV_FILE" && -f "$WORKER_TABLE_CONFIG_FILE" && -f "$CONNECTOR_ENV_FILE" ]]; then
    return 0
  fi

  log "Inicializando entorno local compartido y fixtures temporales"
  make -C "$ROOT_DIR" env-init
}

load_environment() {
  if [[ ! -f "$ENV_FILE" ]]; then
    fail "No se encuentra $ENV_FILE tras la inicialización"
  fi

  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  source "$CONNECTOR_ENV_FILE"
  set +a

  POSTGRES_DB="${POSTGRES_DB:-cdc_sync}"
  POSTGRES_USER="${POSTGRES_USER:-cdc_sync}"
  CONNECT_PORT="${CONNECT_PORT:-8083}"
  DEBEZIUM_POSTGRES_CONNECTOR_NAME="${DEBEZIUM_POSTGRES_CONNECTOR_NAME:-postgres-cdc-source}"
  export WORKER_TABLE_CONFIG_PATH="$E2E_TABLE_CONFIG_PATH"
  WORKER_CLICKHOUSE_DB="${WORKER_CLICKHOUSE_DB:-cdc_sync_analytics}"
  CLICKHOUSE_USER="${CLICKHOUSE_USER:-cdc_sync}"
  CLICKHOUSE_PASSWORD="${CLICKHOUSE_PASSWORD:-cdc_sync}"
}

main() {
  trap cleanup_generated_e2e_table_config EXIT

  require_command docker
  require_command curl
  require_command python3

  if ! docker compose version >/dev/null 2>&1; then
    fail "Docker Compose no esta disponible"
  fi

  prepare_local_environment
  load_environment

  local run_id customer_email customer_name_initial customer_name_updated
  local order_number order_status_initial order_status_updated
  local customer_id order_id customer_insert_version customer_update_version
  local order_insert_version order_update_version
  local e2e_clickhouse_db

  run_id="$(date +%Y%m%d%H%M%S)-$$"
  e2e_clickhouse_db="${E2E_CLICKHOUSE_DB_PREFIX}_${run_id//-/_}"
  export WORKER_CLICKHOUSE_DB="$e2e_clickhouse_db"
  customer_email="e2e-${run_id}@example.com"
  customer_name_initial="E2E Customer ${run_id}"
  customer_name_updated="E2E Customer ${run_id} Updated"
  order_number="E2E-ORDER-${run_id}"
  order_status_initial="created"
  order_status_updated="paid"

  log_json_pairs \
    "Escenario e2e generado" \
    "run_id" "$run_id" \
    "worker_table_config_path" "$WORKER_TABLE_CONFIG_PATH" \
    "clickhouse_database" "$WORKER_CLICKHOUSE_DB" \
    "customer_email" "$customer_email" \
    "customer_name_initial" "$customer_name_initial" \
    "customer_name_updated" "$customer_name_updated" \
    "order_number" "$order_number" \
    "order_status_initial" "$order_status_initial" \
    "order_status_updated" "$order_status_updated"

  log "Levantando stack local"
  compose_up
  log_compose_services

  log "Esperando servicios base"
  wait_for_postgres_ready

  render_connector_config
  apply_connector_config

  log "Esperando conector en RUNNING"
  wait_for_connector_running

  log "Esperando bootstrap de ClickHouse"
  wait_for_clickhouse_tables

  log "Insertando customer de prueba"
  postgres_query "INSERT INTO customers (email, full_name) VALUES ('${customer_email}', '${customer_name_initial}');" >/dev/null
  customer_id="$(trim_output "$(postgres_query "SELECT id FROM customers WHERE email = '${customer_email}';")")"
  [[ -n "$customer_id" ]] || fail "Fallo en fase 'insercion customers': no se pudo resolver el id del customer insertado"
  log_json_pairs \
    "Customer insertado en PostgreSQL" \
    "id" "$customer_id" \
    "email" "$customer_email" \
    "full_name" "$customer_name_initial"

  wait_for_clickhouse_result \
    "insercion customers" \
    "SELECT id, email, full_name, deleted FROM ${WORKER_CLICKHOUSE_DB}.customers FINAL WHERE id = ${customer_id} FORMAT TSVRaw" \
    "${customer_id}"$'\t'"${customer_email}"$'\t'"${customer_name_initial}"$'\t0'
  customer_insert_version="$(trim_output "$(clickhouse_query "SELECT max(version) FROM ${WORKER_CLICKHOUSE_DB}.customers WHERE id = ${customer_id} FORMAT TSVRaw")")"
  [[ "$customer_insert_version" =~ ^[0-9]+$ ]] || fail "Fallo en fase 'insercion customers': no se pudo resolver la version inicial del customer"
  log_clickhouse_json_query \
    "Projection FINAL de customer en ClickHouse" \
    "SELECT id, email, full_name, deleted FROM ${WORKER_CLICKHOUSE_DB}.customers FINAL WHERE id = ${customer_id} FORMAT JSON"
  log_clickhouse_json_query \
    "Versiones observadas de customer tras insert" \
    "SELECT min(version) AS min_version, max(version) AS max_version, count() AS stored_rows FROM ${WORKER_CLICKHOUSE_DB}.customers WHERE id = ${customer_id} FORMAT JSON"

  log "Actualizando customer de prueba"
  postgres_query "UPDATE customers SET full_name = '${customer_name_updated}' WHERE id = ${customer_id};" >/dev/null
  log_json_pairs \
    "Customer actualizado en PostgreSQL" \
    "id" "$customer_id" \
    "full_name" "$customer_name_updated"

  wait_for_clickhouse_number_greater_than \
    "actualizacion customers" \
    "SELECT max(version) FROM ${WORKER_CLICKHOUSE_DB}.customers WHERE id = ${customer_id} FORMAT TSVRaw" \
    "$customer_insert_version"
  customer_update_version="$(trim_output "$(clickhouse_query "SELECT max(version) FROM ${WORKER_CLICKHOUSE_DB}.customers WHERE id = ${customer_id} FORMAT TSVRaw")")"
  log_clickhouse_json_query \
    "Histórico de versiones de customer" \
    "SELECT min(version) AS min_version, max(version) AS max_version, count() AS stored_rows FROM ${WORKER_CLICKHOUSE_DB}.customers WHERE id = ${customer_id} FORMAT JSON"
  wait_for_clickhouse_result \
    "actualizacion customers" \
    "SELECT id, full_name, deleted FROM ${WORKER_CLICKHOUSE_DB}.customers FINAL WHERE id = ${customer_id} FORMAT TSVRaw" \
    "${customer_id}"$'\t'"${customer_name_updated}"$'\t0'
  log_clickhouse_json_query \
    "Projection FINAL de customer tras update" \
    "SELECT id, full_name, deleted FROM ${WORKER_CLICKHOUSE_DB}.customers FINAL WHERE id = ${customer_id} FORMAT JSON"

  log "Insertando order de prueba"
  postgres_query "INSERT INTO orders (customer_id, order_number, total_amount, status) VALUES (${customer_id}, '${order_number}', 44.90, '${order_status_initial}');" >/dev/null
  order_id="$(trim_output "$(postgres_query "SELECT id FROM orders WHERE order_number = '${order_number}';")")"
  [[ -n "$order_id" ]] || fail "Fallo en fase 'insercion orders': no se pudo resolver el id del order insertado"
  log_json_pairs \
    "Order insertado en PostgreSQL" \
    "id" "$order_id" \
    "customer_id" "$customer_id" \
    "order_number" "$order_number" \
    "status" "$order_status_initial"

  wait_for_clickhouse_result \
    "insercion orders" \
    "SELECT id, order_number, status, deleted FROM ${WORKER_CLICKHOUSE_DB}.orders FINAL WHERE id = ${order_id} FORMAT TSVRaw" \
    "${order_id}"$'\t'"${order_number}"$'\t'"${order_status_initial}"$'\t0'
  order_insert_version="$(trim_output "$(clickhouse_query "SELECT max(version) FROM ${WORKER_CLICKHOUSE_DB}.orders WHERE id = ${order_id} FORMAT TSVRaw")")"
  [[ "$order_insert_version" =~ ^[0-9]+$ ]] || fail "Fallo en fase 'insercion orders': no se pudo resolver la version inicial del order"
  log_clickhouse_json_query \
    "Projection FINAL de order en ClickHouse" \
    "SELECT id, order_number, status, deleted FROM ${WORKER_CLICKHOUSE_DB}.orders FINAL WHERE id = ${order_id} FORMAT JSON"
  log_clickhouse_json_query \
    "Versiones observadas de order tras insert" \
    "SELECT min(version) AS min_version, max(version) AS max_version, count() AS stored_rows FROM ${WORKER_CLICKHOUSE_DB}.orders WHERE id = ${order_id} FORMAT JSON"

  log "Actualizando order de prueba"
  postgres_query "UPDATE orders SET status = '${order_status_updated}' WHERE id = ${order_id};" >/dev/null
  log_json_pairs \
    "Order actualizado en PostgreSQL" \
    "id" "$order_id" \
    "status" "$order_status_updated"

  wait_for_clickhouse_number_greater_than \
    "actualizacion orders" \
    "SELECT max(version) FROM ${WORKER_CLICKHOUSE_DB}.orders WHERE id = ${order_id} FORMAT TSVRaw" \
    "$order_insert_version"
  order_update_version="$(trim_output "$(clickhouse_query "SELECT max(version) FROM ${WORKER_CLICKHOUSE_DB}.orders WHERE id = ${order_id} FORMAT TSVRaw")")"
  log_clickhouse_json_query \
    "Histórico de versiones de order" \
    "SELECT min(version) AS min_version, max(version) AS max_version, count() AS stored_rows FROM ${WORKER_CLICKHOUSE_DB}.orders WHERE id = ${order_id} FORMAT JSON"
  wait_for_clickhouse_result \
    "actualizacion orders" \
    "SELECT id, order_number, status, deleted FROM ${WORKER_CLICKHOUSE_DB}.orders FINAL WHERE id = ${order_id} FORMAT TSVRaw" \
    "${order_id}"$'\t'"${order_number}"$'\t'"${order_status_updated}"$'\t0'
  log_clickhouse_json_query \
    "Projection FINAL de order tras update" \
    "SELECT id, order_number, status, deleted FROM ${WORKER_CLICKHOUSE_DB}.orders FINAL WHERE id = ${order_id} FORMAT JSON"

  log "Borrando order de prueba"
  postgres_query "DELETE FROM orders WHERE id = ${order_id};" >/dev/null
  log_json_pairs \
    "Order borrado en PostgreSQL" \
    "id" "$order_id" \
    "order_number" "$order_number"

  wait_for_clickhouse_number_greater_than \
    "delete lógico" \
    "SELECT max(version) FROM ${WORKER_CLICKHOUSE_DB}.orders WHERE id = ${order_id} FORMAT TSVRaw" \
    "$order_update_version"
  log_clickhouse_json_query \
    "Histórico de versiones de order tras delete" \
    "SELECT min(version) AS min_version, max(version) AS max_version, count() AS stored_rows FROM ${WORKER_CLICKHOUSE_DB}.orders WHERE id = ${order_id} FORMAT JSON"
  log_clickhouse_json_query \
    "Projection FINAL de order tras delete lógico" \
    "SELECT id, customer_id, order_number, total_amount, status, created_at, deleted FROM ${WORKER_CLICKHOUSE_DB}.orders FINAL WHERE id = ${order_id} FORMAT JSON"
  wait_for_clickhouse_result \
    "delete lógico" \
    "SELECT id, deleted, isNull(customer_id), isNull(order_number), isNull(total_amount), status, isNull(created_at) FROM ${WORKER_CLICKHOUSE_DB}.orders FINAL WHERE id = ${order_id} FORMAT TSVRaw" \
    "${order_id}"$'\t1\t1\t1\t1\t\t1'

  log "Validación e2e completada correctamente"
}

main "$@"

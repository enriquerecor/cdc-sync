# cdc-sync

Sistema configurable de sincronización CDC entre una base de datos transaccional y una base de datos analítica.

```text
PostgreSQL (OLTP) -> Debezium -> Kafka -> Worker (Python) -> ClickHouse
                      ^
                      |
FastAPI (control plane) -> PostgreSQL (control plane)
                      ^
                      |
Frontend administrativo (React)
```

El repositorio contiene una solución acotada, completa y preparada para evolucionar: API del control plane, consola
administrativa, infraestructura CDC, workers stateless y destino analítico ClickHouse. La configuración funcional se
persiste en PostgreSQL desde la API y la interfaz; cada worker arranca con `WORKER_ID`, solicita su contrato runtime y
mantiene esa configuración en memoria hasta un reinicio manual.

## Requisitos previos

- Docker y Docker Compose.
- `make`.
- `python3`, usado por los scripts del recorrido local.
- `npm`, solo si se ejecutan comandos del frontend fuera de Docker.

## Documentación técnica

- [Stack local](docs/local-stack.md)
- [API REST](docs/api.md)
- [Modelo del control plane](docs/control-plane-model.md)
- [Frontend administrativo](frontend/README.md)
- [Worker](docs/worker.md)
- [PostgreSQL](docs/postgresql.md)
- [Kafka y ZooKeeper](docs/kafka.md)
- [Debezium](docs/debezium.md)
- [ClickHouse](docs/clickhouse.md)

## Recorrido de comprobación

Ejecutar los pasos en orden desde la raíz del repositorio. El recorrido levanta la solución, crea configuración
administrativa, publica CDC, arranca workers, genera cambios, valida la convergencia y deja artefactos fáciles de
capturar para la memoria.

### 1. Preparar el entorno

Qué se comprueba: existen los ficheros locales de entorno necesarios.

```bash
make env-init
```

Resultado esperado:

- existe `.env`;
- existe `frontend/.env`;
- existe `infrastructure/debezium/connectors/generated/postgresql-source.local.env`;
- si ya existían, el comando informa de que no los sobrescribe.

### 2. Levantar servicios base y migrar

Qué se comprueba: la infraestructura local arranca y el control plane tiene su esquema aplicado.

Levantar servicios:

```bash
make demo-up
```

Aplicar migraciones del control plane:

```bash
make demo-migrate
```

Resultado esperado:

- PostgreSQL OLTP, PostgreSQL del control plane, Kafka, Kafka Connect, ClickHouse y la API quedan levantados;
- el esquema ERP/CRM de demo queda aplicado en PostgreSQL OLTP;
- las migraciones de Alembic quedan aplicadas sobre PostgreSQL del control plane.

No continuar al paso siguiente si `make demo-migrate` no termina correctamente. `make api-health` comprueba que la API y
la base responden, pero no sustituye la aplicación de migraciones.

Inspección útil:

```bash
docker compose ps
```

### 3. Levantar la consola administrativa

Qué se comprueba: la API responde y la interfaz puede conectarse al control plane local.

```bash
make api-health
make frontend-up
```

Abrir:

```text
http://localhost:5173
```

Resultado esperado:

- `make api-health` devuelve una respuesta correcta;
- la consola carga con el indicador de API operativo;
- las vistas administrativas aparecen vacías o con datos previos, sin errores.

### 4. Crear configuración administrativa

Qué se comprueba: el control plane registra origen PostgreSQL, destino ClickHouse, workers, configuraciones de tablas y
asignaciones efectivas.

```bash
make demo-configure
```

Resultado esperado:

- se crea o reutiliza el origen `Demo ERP/CRM PostgreSQL local`;
- se crea o reutiliza el destino `Demo ERP/CRM ClickHouse local`;
- se crean los workers `crm-worker`, `sales-worker` y `operations-worker`;
- se crean configuraciones con tablas habilitadas para cada worker;
- cada worker queda asociado a una configuración efectiva;
- se genera `.tmp/e2e-demo-state.json` con el estado local del recorrido.

Volver a `http://localhost:5173` y revisar:

- `Workers`: aparecen `crm-worker`, `sales-worker` y `operations-worker`;
- `Orígenes`: aparece `Demo ERP/CRM PostgreSQL local`;
- `Destinos`: aparece `Demo ERP/CRM ClickHouse local`;
- `Configuraciones`: aparecen las configuraciones creadas para los tres workers;
- la vista de publicación/runtime permite consultar la configuración efectiva asignada.

Resumen de workers y tablas para una tabla de resultados:

```bash
python3 - <<'PY'
import json

with open(".tmp/e2e-demo-state.json", encoding="utf-8") as state_file:
    state = json.load(state_file)

print("| Worker | Tablas asignadas | Destino |")
print("| --- | --- | --- |")
for worker_id, worker in state["workers"].items():
    tables = ", ".join(f"`{table}`" for table in worker["tables"])
    print(f"| `{worker_id}` | {tables} | `cdc_sync_analytics` |")
PY
```

### 5. Materializar CDC en Kafka Connect

Qué se comprueba: la configuración administrativa se convierte en un conector Debezium aplicado de forma idempotente.

En la consola administrativa, ir a `Configuraciones`, localizar el bloque de materialización CDC, seleccionar el origen
`Demo ERP/CRM PostgreSQL local` y pulsar `Materializar CDC`.

Resultado esperado:

- la API compila un conector Debezium PostgreSQL;
- Kafka Connect recibe la configuración;
- la UI muestra el nombre del conector, la clase Debezium, el topic prefix y las tablas capturadas.

Alternativa por terminal:

```bash
make demo-materialize
```

Estado real en Kafka Connect:

```bash
CONNECTOR_NAME="$(
  curl -fsS http://localhost:8083/connectors |
  python3 -c 'import json, sys; print(next(connector for connector in json.load(sys.stdin) if connector.startswith("cdc-sync-postgresql-")))'
)"

curl -fsS "http://localhost:8083/connectors/${CONNECTOR_NAME}/status" | python3 -m json.tool
```

Resultado esperado:

- `connector.state` vale `RUNNING`;
- todas las tareas aparecen en `RUNNING`;
- la lista de tablas capturadas mostrada en la UI incluye tablas de CRM, ventas y operaciones.

### 6. Consultar contrato runtime del worker

Qué se comprueba: el worker obtiene una configuración efectiva remota a partir de su `WORKER_ID`.

En la consola administrativa, dentro de `Configuraciones`, localizar el bloque de runtime, seleccionar
`crm-worker (Demo CRM)` en el campo `WORKER_ID` y pulsar `Consultar runtime`.

Resultado esperado:

- la UI muestra un JSON con `contract_version = 1`;
- el bloque `worker` contiene `worker_id = "crm-worker"`;
- el bloque `kafka` contiene topics CDC de las tablas CRM;
- el bloque `tables` contiene tablas habilitadas como `crm_accounts`.

Para la memoria, usar este fragmento filtrado sin credenciales:

```bash
python3 - <<'PY'
import json
import urllib.request

with urllib.request.urlopen("http://localhost:8000/workers/crm-worker/config") as response:
    runtime_config = json.load(response)

crm_accounts = runtime_config["tables"]["crm_accounts"]
safe_fragment = {
    "contract_version": runtime_config["contract_version"],
    "worker": {
        "worker_id": runtime_config["worker"]["worker_id"],
    },
    "kafka": {
        "group_id": runtime_config["kafka"]["group_id"],
        "topics": [crm_accounts["source"]["topic"]],
    },
    "tables": {
        "crm_accounts": {
            "source": {
                "adapter": crm_accounts["source"]["adapter"],
                "topic": crm_accounts["source"]["topic"],
            },
            "pk": crm_accounts["pk"],
            "sync": crm_accounts["sync"],
        },
    },
}

print(json.dumps(safe_fragment, indent=2, ensure_ascii=False))
PY
```

Resultado esperado:

- el fragmento conserva la información relevante del runtime;
- no contiene credenciales ni secretos.

La respuesta completa también puede consultarse durante depuración local desde terminal, pero no debe usarse como
artefacto público porque incluye credenciales del destino ClickHouse:

```bash
curl -fsS http://localhost:8000/workers/crm-worker/config | python3 -m json.tool
```

### 7. Arrancar workers stateless

Qué se comprueba: los workers arrancan con `WORKER_ID`, cargan su contrato remoto y preparan tablas en ClickHouse.

```bash
make demo-workers
```

Resultado esperado:

- se construye la imagen del worker;
- se arrancan contenedores estables para `crm-worker`, `sales-worker` y `operations-worker`;
- cada worker valida su contrato runtime antes de consumir eventos.

Inspección de logs:

```bash
docker logs --tail 80 cdc-sync-demo-worker-crm-worker | grep -E "worker_started|clickhouse_schema_ready"
docker logs --tail 80 cdc-sync-demo-worker-sales-worker | grep -E "worker_started|clickhouse_schema_ready"
docker logs --tail 80 cdc-sync-demo-worker-operations-worker | grep -E "worker_started|clickhouse_schema_ready"
```

Resultado esperado:

- aparece `worker_started` con `worker_id`, topics, `group_id` y tablas;
- aparece `clickhouse_schema_ready` con la base `cdc_sync_analytics`.

### 8. Generar cambios en PostgreSQL

Qué se comprueba: el origen OLTP recibe cambios representativos de inserción, actualización y borrado.

```bash
make demo-changes
```

Resultado esperado:

- se aplican cambios con claves naturales `DEMO-E2E-*`;
- cada tabla configurada recibe una fila viva actualizada y una fila borrada;
- `.tmp/e2e-demo-state.json` guarda las claves primarias borradas esperadas.

Inspección en PostgreSQL:

```bash
docker compose exec -T postgres psql -U cdc_sync -d cdc_sync -c \
  "SELECT id, account_code, name, status, annual_revenue
   FROM crm_accounts
   WHERE account_code LIKE 'DEMO-E2E-CRM-ACCOUNT-%'
   ORDER BY id;"
```

Resultado esperado:

- aparece la fila viva `DEMO-E2E-CRM-ACCOUNT-LIVE`;
- la fila `DEMO-E2E-CRM-ACCOUNT-DELETE` no aparece porque fue borrada en PostgreSQL;
- la clave borrada queda registrada en el estado de demo.
- Esta tabla se usará en el paso 10 para contrastar historial físico, estado vigente y borrado lógico en ClickHouse.

### 9. Validar la convergencia completa

Qué se comprueba: el recorrido end-to-end reconcilia el origen PostgreSQL y el destino ClickHouse para todas las tablas
configuradas.

```bash
make demo-assert
```

Resultado esperado:

- aparece un resumen `ClickHouse FINAL: estado reconciliado`;
- cada tabla muestra `filas_vivas` y `deletes_lógicos`;
- termina con `PostgreSQL y ClickHouse están reconciliados`.

### 10. Inspeccionar resultados en ClickHouse

Qué se comprueba: los cambios CDC llegan a ClickHouse como escrituras versionadas y el estado vigente se resuelve con
`FINAL`.

Fila viva: comparación entre lectura física y estado vigente:

```bash
docker compose exec -T clickhouse clickhouse-client \
  --user cdc_sync \
  --password=cdc_sync \
  --query "
    SELECT lectura, id, account_code, status, annual_revenue, version, deleted
    FROM
    (
      SELECT '1 sin FINAL' AS lectura, id, account_code, status, annual_revenue, version, deleted
      FROM cdc_sync_analytics.crm_accounts
      WHERE account_code = 'DEMO-E2E-CRM-ACCOUNT-LIVE'
      UNION ALL
      SELECT '2 con FINAL' AS lectura, id, account_code, status, annual_revenue, version, deleted
      FROM cdc_sync_analytics.crm_accounts FINAL
      WHERE account_code = 'DEMO-E2E-CRM-ACCOUNT-LIVE'
        AND deleted = 0
    )
    ORDER BY lectura, version
    FORMAT Pretty"
```

Borrado lógico: comparación entre lectura física y estado vigente:

```bash
DELETED_ACCOUNT_ID="$(python3 -c 'import json; print(json.load(open(".tmp/e2e-demo-state.json"))["deleted_primary_keys"]["crm_accounts"][0])')"

docker compose exec -T clickhouse clickhouse-client \
  --user cdc_sync \
  --password=cdc_sync \
  --query "
    SELECT lectura, id, account_code, status, version, deleted
    FROM
    (
      SELECT '1 sin FINAL' AS lectura, id, account_code, status, version, deleted
      FROM cdc_sync_analytics.crm_accounts
      WHERE id = ${DELETED_ACCOUNT_ID}
      UNION ALL
      SELECT '2 con FINAL' AS lectura, id, account_code, status, version, deleted
      FROM cdc_sync_analytics.crm_accounts FINAL
      WHERE id = ${DELETED_ACCOUNT_ID}
    )
    ORDER BY lectura, version
    FORMAT Pretty"
```

Comparación PostgreSQL frente a ClickHouse:

```bash
docker compose exec -T postgres psql -U cdc_sync -d cdc_sync -c \
  "SELECT id, account_code, status, annual_revenue
   FROM crm_accounts
   WHERE account_code = 'DEMO-E2E-CRM-ACCOUNT-LIVE';"

docker compose exec -T clickhouse clickhouse-client \
  --user cdc_sync \
  --password=cdc_sync \
  --query "
    SELECT id, account_code, status, annual_revenue
    FROM cdc_sync_analytics.crm_accounts FINAL
    WHERE account_code = 'DEMO-E2E-CRM-ACCOUNT-LIVE'
      AND deleted = 0
    FORMAT Pretty"
```

Resultado esperado:

- `sin FINAL` lee las filas físicas disponibles en ese momento;
- `con FINAL` fuerza el estado resuelto por ClickHouse;
- si ambas lecturas coinciden, ClickHouse ya ha compactado las partes en segundo plano;
- la fila viva queda con `deleted = 0`;
- la clave borrada queda resuelta como lápida con `deleted = 1`;
- los valores funcionales de PostgreSQL y ClickHouse coinciden para la fila viva.

## Atajos y comandos de apoyo

Recorrido completo automático desde una instalación limpia:

```bash
make env-init
make e2e-validate
```

`make demo-local` ejecuta el mismo recorrido completo y `make e2e-validate` delega en él.

Arranque administrativo mínimo, útil para crear configuración manualmente desde la consola:

```bash
make env-init
make api-migrate
make frontend-up
make api-health
```

Workers manuales para configuraciones creadas desde la consola:

```bash
make workers-up WORKER_IDS=crm-worker,sales-worker
make workers-down WORKER_IDS=crm-worker,sales-worker
```

Tests por capas:

| Capa | Comando | Resultado esperado |
| --- | --- | --- |
| Dominio, API y control plane | `make api-test` | Suite `pytest` de API en contenedor de test. |
| Repositorio SQL e integración | `make api-test-integration` | PostgreSQL efímero y tests de repositorio. |
| Worker y normalización | `make worker-test` | Tests del worker con entorno virtual local. |
| Frontend administrativo | `npm --prefix frontend run smoke:admin` | Smoke Playwright con API mockeada. |
| Validación end-to-end | `make e2e-validate` | Recorrido completo con servicios reales. |

Reset local:

```bash
make workers-down WORKER_IDS=crm-worker,sales-worker,operations-worker
docker compose down -v
rm -f .tmp/e2e-demo-state.json
```

## Puntos de inspección para resultados

Esta sección resume qué artefactos capturar una vez ejecutado el recorrido anterior.

| Evidencia | Artefacto recomendado | Cómo obtenerlo |
| --- | --- | --- |
| Fig. 4-1 | Consola administrativa en una vista de configuración | Abrir `http://localhost:5173` tras el paso 4 y usar la vista `Configuraciones`. |
| Tabla 4-1 | Resumen de workers, tablas y destino | Usar el resumen Python del paso 4. |
| Fig. 4-2 | Conector Debezium y tablas capturadas | Usar el resultado mostrado por la UI en el paso 5. |
| Código 4-1 | Fragmento del contrato runtime sin credenciales | Consultar el runtime en la UI y usar el fragmento seguro del paso 6. |
| Fig. 4-3 | Logs de arranque del worker | Usar los logs filtrados del paso 7. |
| Código 4-2 | Lectura física y estado vigente de una fila viva | Usar la primera consulta de ClickHouse del paso 10. |
| Código 4-3 | Comparación PostgreSQL frente a ClickHouse vigente | Usar las dos consultas de comparación del paso 10. |
| Código 4-4 | Lectura física y estado vigente de un borrado lógico | Usar la consulta de `DELETED_ACCOUNT_ID` del paso 10. |
| Fig. 4-4 | Comparación PostgreSQL frente a ClickHouse | Usar las dos consultas de comparación del paso 10. |
| Fig. 4-5 | Salida resumida de validación completa | Capturar el tramo final de `make demo-assert` en el paso 9, o de `make e2e-validate`. |
| Tabla 4-2 | Pruebas por capa | Usar la tabla de tests por capas y completar resultados con la salida real de cada comando. |

# Worker

## Alcance en esta fase

- consumidor base en Python
- suscripción a los topics CDC habilitados en la configuración
- normalización de eventos CDC a un contrato interno común
- bootstrap idempotente de base y tablas en ClickHouse al arranque
- persistencia versionada de eventos normalizados en ClickHouse

## Arranque

Preparar la configuración local del worker:

```bash
make env-init
```

Esto crea `worker/config/tables.json` a partir de `worker/config/tables.example.json` si todavía no existe.

El worker arranca ya con un contrato técnico propio:

- `WORKER_ID`
- `WORKER_CONTROL_PLANE_BASE_URL`

La petición real a `GET /workers/{id}/config` queda fuera de esta fase. Hasta #28, el JSON local y las variables de
ClickHouse se mantienen como fixture de desarrollo para no romper la validación extremo a extremo.

Contrato mínimo actual del fixture de tablas:

- `version`
- `tables`

Configuración global temporal de destino:

- `WORKER_CLICKHOUSE_HOST`
- `WORKER_CLICKHOUSE_PORT`
- `WORKER_CLICKHOUSE_SECURE`
- `WORKER_CLICKHOUSE_DB`
- `WORKER_CLICKHOUSE_USER`
- `WORKER_CLICKHOUSE_PASSWORD`

Valores recomendados:

- entorno local: `WORKER_CLICKHOUSE_PORT=9000` y `WORKER_CLICKHOUSE_SECURE=false`
- ClickHouse Cloud: `WORKER_CLICKHOUSE_PORT=9440` y `WORKER_CLICKHOUSE_SECURE=true`

Ejemplo mínimo para ClickHouse Cloud:

```bash
WORKER_CLICKHOUSE_HOST=<cluster>.clickhouse.cloud
WORKER_CLICKHOUSE_PORT=9440
WORKER_CLICKHOUSE_SECURE=true
WORKER_CLICKHOUSE_DB=cdc_sync_analytics
WORKER_CLICKHOUSE_USER=<usuario>
WORKER_CLICKHOUSE_PASSWORD=<password>
```

Si se detecta una combinación sospechosa entre puerto y TLS, el worker emitirá un `warning`
para facilitar la detección de configuraciones incoherentes sin bloquear despliegues custom.

Contrato mínimo actual por tabla:

- `enabled`
- `source.adapter`
- `source.connection`
- `source.schema` (opcional)
- `source.table`
- `source.topic`
- `pk`
- `sync.mode`
- `destination.table`
- `destination.default_nullable` (opcional)
- `destination.columns[].name`
- `destination.columns[].type`
- `destination.columns[].nullable` (opcional)

Restricciones de `destination.columns`:

- debe incluir todas las columnas de PK declaradas en `pk`
- las columnas de PK no pueden ser `nullable`
- no se pueden declarar las columnas técnicas `version` y `deleted`; las añadirá el sistema
- si una columna no declara `nullable`, heredará `destination.default_nullable`
- si tampoco existe `destination.default_nullable`, la nulabilidad efectiva será `false`

Arrancar el servicio:

```bash
docker compose up -d --build worker
```

Topics por defecto:

- `cdc_sync.public.customers`
- `cdc_sync.public.orders`

Los topics se derivan del fichero de tablas mediante `source.topic`.
El adapter usado para cada tabla se declara en `source.adapter`.
La ruta del fichero de tablas se configura mediante `WORKER_TABLE_CONFIG_PATH` en `.env`.
En esta fase esa ruta no debe interpretarse como fuente de verdad del MVP, sino como compatibilidad local hasta la carga
remota desde el control plane.

## Contrato normalizado

El worker transforma cada evento CDC soportado a un `NormalizedEvent` con estos campos:

- `table`
- `primary_key`
- `data`
- `version`
- `source_position`
- `deleted`
- `operation`

Semantica actual:

- `insert`, `update` y `snapshot` exponen la fila normalizada en `data`
- `delete` expone `primary_key`, `version`, `source_position`, `deleted=true` y `data={}`
- `version` es un valor comparable por PK para resolver el estado final en el pipeline y en el sink
- `source_position` conserva la metadata de posicion original del origen para trazabilidad y futuros adapters
- para Debezium PostgreSQL, `version` se resuelve de forma estricta desde `payload.source.lsn`
- para Debezium PostgreSQL, `source_position` se expone como `{"lsn": <valor>}`
- `missing` y `null` no son equivalentes: un upsert debe incluir todas las columnas configuradas en destino
- los deletes lógicos se materializan con PK + columnas técnicas; el flag `deleted` marca el borrado
- cuando una columna no PK es `nullable=false`, ClickHouse materializa su valor por defecto en el delete logico porque esa columna no se inserta en la fila de borrado

## Validaciones

Comprobar que el servicio está levantado:

```bash
docker compose ps
```

Seguir logs:

```bash
docker compose logs -f worker
```

Resultado esperado al arrancar:

- aparece una línea `worker_started` con `worker_id` y `control_plane_base_url`
- aparece una línea `clickhouse_schema_ready`

## Tests

> Este flujo usa `.venv` y `worker/requirements-dev.txt`, y no modifica la imagen runtime del worker.

Preparar el entorno virtual local del repo con las dependencias de desarrollo del worker:

```bash
make worker-test-deps
```

Ejecutar la suite de tests del worker:

```bash
make worker-test
```

## Validación de consumo

La validación reproducible recomendada del flujo completo está en:

```bash
make e2e-validate
```

Este comando levanta el stack, aplica el conector y comprueba automáticamente el comportamiento e2e sobre
`customers` y `orders`.

## Diagnóstico manual del worker

Registrar el conector si el stack se ha levantado desde cero:

```bash
make debezium-postgres-apply
make debezium-postgres-status
```

Insertar una fila en `customers`:

```bash
docker compose exec postgres psql -U cdc_sync -d cdc_sync -c \
  "INSERT INTO customers (email, full_name) VALUES ('worker-check@example.com', 'Worker Check Customer');"
```

Resultado esperado:

- aparece una fila versionada en ClickHouse:

```bash
docker compose exec clickhouse clickhouse-client --query \
  "SELECT id, email, full_name, deleted FROM cdc_sync_analytics.customers FINAL WHERE email = 'worker-check@example.com'"
```

- el resultado incluye la fila insertada con `deleted = 0`

Validar también `orders`:

```bash
docker compose exec postgres psql -U cdc_sync -d cdc_sync -c \
  "INSERT INTO orders (customer_id, order_number, total_amount, status) VALUES ((SELECT id FROM customers WHERE email = 'worker-check@example.com'), 'WORKER-CHECK-ORDER', 44.90, 'created');"
```

Resultado esperado:

- aparece una fila versionada en ClickHouse:

```bash
docker compose exec clickhouse clickhouse-client --query \
  "SELECT order_number, status, deleted FROM cdc_sync_analytics.orders FINAL WHERE order_number = 'WORKER-CHECK-ORDER'"
```

- el resultado incluye la fila insertada con `deleted = 0`

## Nota sobre offsets

En el primer arranque del grupo `cdc-sync-worker`, la estrategia `earliest` puede reproducir primero eventos
históricos del topic. Para validar el evento nuevo, buscar en logs el valor insertado.

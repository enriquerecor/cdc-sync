# Worker

## Alcance en esta fase

- consumidor base en Python
- suscripción a los topics CDC habilitados en la configuración
- normalización de eventos CDC a un contrato interno común
- bootstrap idempotente de base y tablas en ClickHouse al arranque
- persistencia versionada de eventos normalizados en ClickHouse

## Arranque

Preparar la configuracion local del worker:

```bash
make env-init
```

Esto crea `worker/config/tables.json` a partir de `worker/config/tables.example.json` si todavia no existe.

El fichero real de configuracion del entorno no se versiona. El ejemplo versionado define el contrato base esperado
por el worker.

Contrato minimo actual:

- `version`
- `tables`

Configuracion global de destino actual:

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

Si se detecta una combinacion sospechosa entre puerto y TLS, el worker emitira un `warning`
para facilitar la deteccion de configuraciones incoherentes sin bloquear despliegues custom.

Contrato minimo actual por tabla:

- `enabled`
- `source.adapter`
- `source.connection`
- `source.schema` (opcional)
- `source.table`
- `source.topic`
- `pk`
- `sync.mode`
- `destination.table`
- `destination.columns[].name`
- `destination.columns[].type`
- `destination.columns[].nullable`

Restricciones de `destination.columns`:

- debe incluir todas las columnas de PK declaradas en `pk`
- las columnas de PK no pueden ser `nullable`
- no se pueden declarar las columnas tecnicas `version` y `deleted`; las anadira el sistema

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

- aparece una línea `worker_started`
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

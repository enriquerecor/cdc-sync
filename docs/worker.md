# Worker

## Alcance en esta fase

- arranque stateless con `WORKER_ID`
- carga inicial de configuración runtime desde el control plane
- suscripción a los topics CDC incluidos en el contrato remoto
- normalización de eventos CDC a un contrato interno común
- bootstrap idempotente de base y tablas en ClickHouse al arranque
- persistencia versionada de eventos normalizados en ClickHouse

## Arranque

El worker solo necesita dos variables de entorno:

- `WORKER_ID`
- `WORKER_CONTROL_PLANE_BASE_URL`

Al arrancar, solicita:

```http
GET /workers/{WORKER_ID}/config
```

La respuesta se valida de forma estricta antes de crear el consumidor Kafka o conectar con ClickHouse. El proceso falla
si la API no está disponible, si el worker no existe, si no tiene configuración efectiva o si el contrato recibido no es
compatible.

La configuración se mantiene fija en memoria durante toda la vida del proceso. Cualquier cambio administrativo hecho
desde la API o desde la interfaz requiere reiniciar manualmente el worker para surtir efecto.

## Responsabilidades

El worker no usa JSON local de tablas ni variables locales de Kafka o ClickHouse como fuente de verdad funcional.
Tampoco conoce credenciales de origen ni gestiona conectores CDC; esas responsabilidades pertenecen al control plane y a
Kafka Connect.

El contrato runtime debe incluir:

- `contract_version`
- `worker.worker_id`
- `kafka.bootstrap_servers`
- `kafka.client_id`
- `kafka.group_id`
- `kafka.auto_offset_reset`
- `kafka.poll_timeout_ms`
- `kafka.topics`
- `destination` ClickHouse con credenciales de destino
- `tables` habilitadas con `source`, `pk`, `sync` y `destination`

El worker soporta en esta fase:

- `contract_version=1`
- `source.adapter=debezium_postgres`
- `sync.mode=realtime`
- `destination.adapter=clickhouse`

## Contrato normalizado

El worker transforma cada evento CDC soportado a un `NormalizedEvent` con estos campos:

- `table`
- `primary_key`
- `data`
- `version`
- `source_position`
- `deleted`
- `operation`

Semántica actual:

- `insert`, `update` y `snapshot` exponen la fila normalizada en `data`
- `delete` expone `primary_key`, `version`, `source_position`, `deleted=true` y `data={}`
- `version` es un valor comparable por PK para resolver el estado final en el pipeline y en el sink
- `source_position` conserva la metadata de posición original del origen para trazabilidad y futuros adapters
- para Debezium PostgreSQL, `version` se resuelve de forma estricta desde `payload.source.lsn`
- para Debezium PostgreSQL, `source_position` se expone como `{"lsn": <valor>}`
- `missing` y `null` no son equivalentes: un upsert debe incluir todas las columnas configuradas en destino
- los deletes lógicos se materializan con PK + columnas técnicas; el flag `deleted` marca el borrado

## Validaciones

Comprobar que el servicio está levantado:

```bash
docker compose ps
```

Seguir logs:

```bash
docker compose logs -f worker
```

Resultado esperado al arrancar con configuración efectiva válida:

- aparece una línea `worker_started` con `worker_id`, `control_plane_base_url` y `runtime_contract_version`
- aparece una línea `clickhouse_schema_ready`

Si falta la configuración remota, el contenedor queda parado con el error explícito en logs. En esta fase el servicio no
usa `restart: unless-stopped` para no ocultar fallos de configuración detrás de un bucle de reinicios.

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

## Validación extremo a extremo

La validación reproducible completa vive en la demo multi-worker:

```bash
make demo-local
```

También puede ejecutarse por pasos con `make demo-workers`, `make demo-changes` y `make demo-assert` cuando se quiera
depurar solo el comportamiento runtime del worker.

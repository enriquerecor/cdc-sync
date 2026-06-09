# API REST

## Alcance en esta fase

- base técnica del control plane con FastAPI
- persistencia propia en PostgreSQL separada del PostgreSQL OLTP del stack CDC
- migraciones iniciales con Alembic
- separación mínima entre dominio, aplicación, HTTP e infraestructura
- routing base y `healthcheck`
- API administrativa mínima para workers, conexiones, destinos, configuraciones y asignaciones efectivas
- contrato runtime por worker para el data plane

## Estructura

El backend vive en `api/` y se organiza así:

- `src/cdc_sync_api/domain`: tipos del dominio
- `src/cdc_sync_api/application`: casos de uso, DTOs y puertos
- `src/cdc_sync_api/infrastructure`: persistencia y adaptadores técnicos
- `src/cdc_sync_api/entrypoints/http`: FastAPI y routing HTTP
- `alembic/`: migraciones

## Arranque local

Preparar ficheros de entorno:

```bash
make env-init
```

La API no carga automáticamente un `.env` del repositorio. En Docker recibe sus variables desde `docker-compose.yml`.
Para ejecutarla fuera de Docker puede usarse `api/.env.example` como plantilla local.

Aplicar migraciones sobre PostgreSQL del control plane:

```bash
make api-migrate
```

Levantar la API:

```bash
make api-up
```

Comprobar salud:

```bash
make api-health
```

Resultado esperado:

- `GET /health` responde `200 OK` con el estado del servicio y de la base de datos
- `GET /api/v1` expone el routing base y las URLs de documentación del backend
- Swagger UI queda disponible en `http://localhost:8000/docs`

## OpenAPI y Postman

FastAPI genera el contrato OpenAPI a partir de las rutas y schemas HTTP. El repositorio no versiona un
`openapi.json` estático para evitar divergencias con el código.

Con la API levantada, se puede inspeccionar el contrato en:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

Swagger UI permite probar los endpoints principales desde el navegador. El JSON de OpenAPI puede importarse en Postman
usando la opción de importar desde URL y pegando:

```text
http://localhost:8000/openapi.json
```

Postman puede generar una colección a partir de esa especificación para explorar o ejecutar peticiones contra la API
local. Esta colección no se versiona en el repositorio en esta fase: debe generarse desde el contrato actual cuando se
quiera revisar o demostrar la API. Los tests automatizados del proyecto siguen viviendo en `pytest`.

La demo reproducible completa de la vertical multi-worker, con workers reales consumiendo eventos y escribiendo en
ClickHouse, está documentada en [local-stack.md](local-stack.md).

## API administrativa

La API administrativa vive bajo `/api/v1` y usa JSON con campos `snake_case`.
Permite crear, consultar, modificar y eliminar la configuración administrativa del control plane:

- `/api/v1/workers`
- `/api/v1/source-connections`
- `/api/v1/destinations`
- `/api/v1/configs`
- `/api/v1/workers/{worker_internal_id}/config-assignment`
- `/api/v1/source-connections/{source_connection_id}/cdc-connector`

`configs` se gestionan como agregado completo: una configuración incluye sus tablas, claves primarias y columnas de
destino. Al actualizar una configuración se reemplaza el agregado completo persistido.

Las conexiones de origen y destinos aceptan credenciales en operaciones de escritura mediante:

```json
{
  "credentials": {
    "user": "cdc_sync",
    "password": "cdc_sync"
  }
}
```

Las respuestas administrativas no devuelven secretos ni `credentials_secret_id`; solo indican que las credenciales
están configuradas. Esta decisión mantiene el contrato HTTP separado del detalle interno de persistencia de secretos.

La asignación efectiva se actualiza con:

```http
PUT /api/v1/workers/{worker_internal_id}/config-assignment
```

```json
{
  "config_id": "00000000-0000-0000-0000-000000000000"
}
```

Asignar o editar una configuración cambia la fuente de verdad administrativa. El worker carga el contrato runtime al
arrancar y mantiene esa configuración fija hasta el siguiente reinicio manual.

Los workers aceptan `kafka_group_id` opcional en creación y actualización. Si no se informa, el contrato runtime deriva
el grupo efectivo como `cdc-sync-worker-{worker_id}`. La API rechaza workers cuyo grupo efectivo colisione con el de
otro worker, tanto si el grupo viene persistido como si se deriva.

La consola administrativa consume actualmente los CRUD de workers, conexiones de origen y destinos. La gestión visual
de configuraciones, asignaciones y materialización CDC queda para la siguiente fase de frontend, aunque esos endpoints
ya formen parte del contrato de la API y de la demo e2e.

## Contrato runtime del worker

El endpoint de data plane vive fuera de `/api/v1`:

```http
GET /workers/{worker_id}/config
```

`worker_id` es el identificador operativo usado por `WORKER_ID`, no el UUID interno administrativo. La respuesta
devuelve solo lo que el worker necesita para consumir Kafka y escribir en ClickHouse:

```json
{
  "contract_version": 1,
  "worker": {
    "worker_id": "local-worker"
  },
  "kafka": {
    "bootstrap_servers": "kafka:29092",
    "client_id": "cdc-sync-worker-local-worker",
    "group_id": "cdc-sync-worker-local-worker",
    "auto_offset_reset": "earliest",
    "poll_timeout_ms": 1000,
    "topics": ["cdc_sync.public.customers"]
  },
  "destination": {
    "adapter": "clickhouse",
    "host": "clickhouse",
    "port": 9000,
    "secure": false,
    "database": "cdc_sync_analytics",
    "credentials": {
      "user": "cdc_sync",
      "password": "cdc_sync"
    }
  },
  "tables": {
    "customers": {
      "enabled": true,
      "source": {
        "adapter": "debezium_postgres",
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
        "columns": [
          { "name": "id", "type": "UInt64", "nullable": false }
        ]
      }
    }
  }
}
```

El contrato incluye solo tablas habilitadas de una configuración habilitada. No expone credenciales de origen,
`credentials_secret_id`, payloads internos de secretos ni configuración Debezium o Kafka Connect. Si el worker no
existe o no tiene configuración efectiva, la API devuelve `404`. Si la configuración administrativa publicada está rota
o es incompatible con el runtime, devuelve `422`.

## Materialización CDC

El control plane materializa conectores CDC mediante una operación administrativa explícita:

```http
PUT /api/v1/source-connections/{source_connection_id}/cdc-connector
```

La operación compila un conector CDC para la conexión de origen indicada y lo aplica de forma idempotente en Kafka
Connect con `PUT /connectors/{name}/config`.

El caso de uso es agnóstico del motor OLTP: selecciona un compilador por `source_type` y falla de forma explícita si no
existe un adapter disponible. En el MVP solo está implementado el adapter Debezium PostgreSQL.

Respuesta esperada:

```json
{
  "connector_name": "cdc-sync-postgresql-00000000-0000-0000-0000-000000000000",
  "source_connection_id": "00000000-0000-0000-0000-000000000000",
  "source_type": "postgresql",
  "connector_class": "io.debezium.connector.postgresql.PostgresConnector",
  "topic_prefix": "cdc_sync",
  "captured_tables": ["public.customers", "public.orders"]
}
```

La respuesta no expone credenciales. Si la configuración administrativa no permite compilar un conector válido, la API
devuelve `422`. Si Kafka Connect no está disponible o rechaza la configuración, devuelve `502`.

## Variables principales

- `API_PORT`
- `API_NAME`
- `API_VERSION`
- `API_KAFKA_CONNECT_BASE_URL`
- `API_WORKER_KAFKA_BOOTSTRAP_SERVERS`
- `API_WORKER_KAFKA_CLIENT_ID_PREFIX`
- `API_WORKER_KAFKA_AUTO_OFFSET_RESET`
- `API_WORKER_KAFKA_POLL_TIMEOUT_MS`
- `API_CORS_ALLOWED_ORIGINS`
- `CONTROL_PLANE_POSTGRES_DB`
- `CONTROL_PLANE_POSTGRES_USER`
- `CONTROL_PLANE_POSTGRES_PASSWORD`
- `CONTROL_PLANE_POSTGRES_PORT`
- `API_DATABASE_HOST`
- `API_DATABASE_PORT`
- `API_DATABASE_NAME`
- `API_DATABASE_USER`
- `API_DATABASE_PASSWORD`
- `API_DATABASE_ECHO`

En Docker, `API_DATABASE_HOST`, `API_DATABASE_PORT`, `API_DATABASE_NAME`, `API_DATABASE_USER` y
`API_DATABASE_PASSWORD` se inyectan con valores internos del stack. En ejecución local fuera de Docker, esos valores
deben venir del entorno del proceso.

`API_CORS_ALLOWED_ORIGINS` acepta una lista separada por comas con los orígenes permitidos para el frontend local. El
valor por defecto del entorno local permite `http://localhost:5173` y `http://127.0.0.1:5173`.

## Tests mínimos

Ejecutar la suite rápida de la API:

```bash
make api-test
```

La imagen runtime de la API instala solo las dependencias de ejecución. Los tests se ejecutan con un stage
independiente del `Dockerfile` para no arrastrar `pytest` ni utilidades de desarrollo al contenedor del servicio.

Los tests de integración del repositorio SQLAlchemy requieren PostgreSQL real y se ejecutan de forma separada:

```bash
make api-test-integration
```

Este objetivo levanta un PostgreSQL efímero en Docker, inyecta `API_TEST_DATABASE_URL` y ejecuta solo los tests de
integración del repositorio. Esos tests no usan la base normal de la API y fallan de forma explícita si la URL indicada
no apunta a una base de datos de test.

## Nota de arquitectura

La API mantiene separadas las capas de dominio, aplicación, HTTP e infraestructura. El modelo persistente del control
plane vive en PostgreSQL bajo el schema `control_plane` y representa workers, conexiones de origen, destinos,
configuraciones de tablas y asignación efectiva por worker. El contrato runtime del worker se compila desde ese modelo,
pero no expone sus identificadores internos ni los detalles de materialización de Kafka Connect.

La documentación del modelo y sus límites de MVP está en `docs/control-plane-model.md`.

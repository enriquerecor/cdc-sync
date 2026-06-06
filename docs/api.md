# API REST

## Alcance en esta fase

- base técnica del control plane con FastAPI
- persistencia propia en PostgreSQL separada del PostgreSQL OLTP del stack CDC
- migraciones iniciales con Alembic
- separación mínima entre dominio, aplicación, HTTP e infraestructura
- routing base y `healthcheck`
- API administrativa mínima para workers, conexiones, destinos, configuraciones y asignaciones efectivas

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

Levantar PostgreSQL del control plane y la API:

```bash
make api-up
```

Aplicar migraciones:

```bash
make api-migrate
```

Comprobar salud:

```bash
make api-health
```

Resultado esperado:

- `GET /health` responde `200 OK` con el estado del servicio y de la base de datos
- `GET /api/v1` expone el routing base del backend
- OpenAPI queda disponible en `http://localhost:8000/docs`

## API administrativa

La API administrativa vive bajo `/api/v1` y usa JSON con campos `snake_case`.
Permite crear, consultar, modificar y eliminar la configuración administrativa del control plane:

- `/api/v1/workers`
- `/api/v1/source-connections`
- `/api/v1/destinations`
- `/api/v1/configs`
- `/api/v1/workers/{worker_internal_id}/config-assignment`

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

En esta fase, asignar o editar una configuración solo cambia la fuente de verdad administrativa. El worker seguirá
aplicando cambios tras reinicio manual cuando se implemente el contrato runtime remoto de las siguientes issues.

## Variables principales

- `API_PORT`
- `API_NAME`
- `API_VERSION`
- `API_KAFKA_CONNECT_BASE_URL`
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
configuraciones de tablas y asignación efectiva por worker.

Esta fase no expone todavía el contrato runtime del worker. La documentación del modelo y sus límites de MVP está en
`docs/control-plane-model.md`.

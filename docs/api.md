# API REST

## Alcance en esta fase

- base técnica del control plane con FastAPI
- persistencia propia en PostgreSQL separada del PostgreSQL OLTP del stack CDC
- migraciones iniciales con Alembic
- separación mínima entre dominio, aplicación, HTTP e infraestructura
- routing base y `healthcheck`

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

## Variables principales

- `API_PORT`
- `API_NAME`
- `API_VERSION`
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

## Tests mínimos

Ejecutar la verificación básica del `healthcheck`:

```bash
make api-test
```

La imagen runtime de la API instala solo las dependencias de ejecución. Los tests se ejecutan con un stage
independiente del `Dockerfile` para no arrastrar `pytest` ni utilidades de desarrollo al contenedor del servicio.

## Nota de arquitectura

La API mantiene separadas las capas de dominio, aplicación, HTTP e infraestructura. El modelo persistente del control
plane vive en PostgreSQL bajo el schema `control_plane` y representa workers, conexiones de origen, destinos,
configuraciones de tablas y asignación efectiva por worker.

Esta fase no expone todavía endpoints administrativos ni el contrato runtime del worker. La documentación del modelo y
sus límites de MVP está en `docs/control-plane-model.md`.

# API REST

## Alcance en esta fase

- base técnica del control plane con FastAPI
- persistencia propia en PostgreSQL separada del PostgreSQL OLTP del stack CDC
- migraciones con Alembic
- configuración en edición del MVP con persistencia propia
- validación previa a escritura y control básico de concurrencia con `version`
- routing base, `healthcheck` y endpoints de `editing-config`

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

La API ya diferencia la configuración en edición del futuro contrato publicado del worker. En `#17` solo se gestiona
la configuración editable; `#18` materializará la configuración activa compilada sin acoplar el contrato externo a la
persistencia interna del backend.

## Configuración en edición

La configuración editable del MVP vive en una única raíz `config_editing` con control básico de concurrencia mediante
`version`. Ese valor lo genera PostgreSQL con una secuencia monotónica y no se reutiliza tras borrar y recrear la
configuración. El campo `updated_at` queda como metadato de auditoría.

Endpoints disponibles en esta fase:

- `GET /api/v1/editing-config`
- `PUT /api/v1/editing-config`
- `DELETE /api/v1/editing-config`

`PUT` valida primero todo el documento en memoria y solo abre transacción cuando la configuración ya es coherente.
Si ya existe configuración en edición, el cliente debe enviar `expected_version`; si no coincide con el persistido,
la API responde `409 Conflict`.

`DELETE` también exige `expected_version` cuando existe configuración en edición. Si el valor no coincide con el
persistido, la API responde `409 Conflict` y evita borrar cambios más recientes.

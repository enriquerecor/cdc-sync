# Frontend administrativo

Base técnica del frontend MVP de `cdc-sync`.

La aplicación usa Vite, React, TypeScript y Mantine. Permite gestionar las entidades administrativas base del control
plane: workers, conexiones de origen y destinos analíticos.

## Configuración

Crear los ficheros locales de entorno desde la raíz del repositorio:

```bash
make env-init
```

Este comando crea `frontend/.env` desde `frontend/.env.example` si todavía no existe. También prepara el `.env` general
del stack Docker y el fixture local de Debezium.

También puede crearse manualmente:

```bash
cp frontend/.env.example frontend/.env
```

Variable principal:

- `VITE_API_BASE_URL`: URL base de la API REST consumida por el navegador. Por defecto, `http://localhost:8000`.

## Desarrollo con npm

Preparar la base del control plane, arrancar la API y comprobar que responde:

```bash
make env-init
make api-migrate
make api-up
make api-health
```

Instalar dependencias y arrancar Vite:

```bash
make frontend-install
make frontend-dev
```

La UI queda disponible en:

```text
http://localhost:5173
```

## Uso básico

La consola incluye tres CRUDs administrativos:

- Workers: alta, edición, activación/desactivación y eliminación.
- Orígenes: alta, edición y eliminación de conexiones de origen.
- Destinos: alta, edición y eliminación de destinos analíticos.

Los motores se seleccionan desde catálogos internos. En el MVP solo están habilitados PostgreSQL como origen y
ClickHouse como destino, pero las vistas no quedan acopladas a esas tecnologías concretas.

Las respuestas de lectura no contienen secretos. En creación, usuario y contraseña son obligatorios para orígenes y
destinos. En edición, las credenciales se envían solo si se rellenan explícitamente los dos campos.

La pestaña de configuraciones queda reservada para el flujo posterior de tablas, asignaciones, materialización CDC y
runtime.

## Desarrollo con Docker Compose

El frontend está integrado en el stack local como servicio de desarrollo. Ruta recomendada:

```bash
make env-init
make api-migrate
make frontend-up
make frontend-logs
```

También puede arrancarse directamente:

```bash
docker compose up frontend
```

`make frontend-up` levanta el frontend y sus dependencias declaradas, pero no aplica migraciones. Por eso
`make api-migrate` debe ejecutarse antes en entornos nuevos.

El servicio usa `FRONTEND_API_BASE_URL` desde `.env` para inyectar `VITE_API_BASE_URL` en Vite. Esta imagen es solo de
desarrollo; no incluye Nginx, build estático productivo ni configuración runtime para producción.

## Tipos OpenAPI

Con la API levantada:

```bash
make frontend-api-types
```

El script usa por defecto:

```text
http://localhost:8000/openapi.json
```

Puede apuntarse a otra API local con:

```bash
OPENAPI_BASE_URL=http://localhost:8001 npm --prefix frontend run api:types
```

## Build

```bash
make frontend-build
```

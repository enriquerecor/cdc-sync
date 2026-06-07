# Frontend administrativo

Base técnica del frontend MVP de `cdc-sync`.

La aplicación usa Vite, React, TypeScript y Mantine. En esta fase solo prepara el layout administrativo, la integración
con la API y el cliente HTTP tipado; no implementa CRUD de workers, conexiones, destinos ni configuraciones.

## Configuración

Crear el fichero local de entorno:

```bash
make env-init
```

También puede crearse manualmente:

```bash
cp frontend/.env.example frontend/.env
```

Variable principal:

- `VITE_API_BASE_URL`: URL base de la API REST consumida por el navegador. Por defecto, `http://localhost:8000`.

## Desarrollo con npm

Arrancar la API y aplicar migraciones:

```bash
make api-up
make api-migrate
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

## Desarrollo con Docker Compose

El frontend está integrado en el stack local como servicio de desarrollo:

```bash
make frontend-up
make frontend-logs
```

También puede arrancarse directamente:

```bash
docker compose up frontend
```

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

# Frontend administrativo

Base técnica del frontend MVP de `cdc-sync`.

La aplicación usa Vite, React, TypeScript y Mantine. Permite gestionar workers, conexiones de origen, destinos
analíticos, configuraciones de sincronización y operaciones de publicación del MVP.

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

La consola incluye los flujos administrativos principales:

- Workers: alta, edición, activación/desactivación y eliminación.
- Orígenes: alta, edición y eliminación de conexiones de origen.
- Destinos: alta, edición y eliminación de destinos analíticos.
- Configuraciones: alta, edición y eliminación del agregado completo con tablas, claves primarias y columnas destino.
- Publicación: asignación efectiva de una configuración a un worker y materialización CDC del origen.
- Runtime: consulta de solo lectura del contrato publicado con `GET /workers/{worker_id}/config`.

Los motores se seleccionan desde catálogos internos. En el MVP solo están habilitados PostgreSQL como origen y
ClickHouse como destino, pero las vistas no quedan acopladas a esas tecnologías concretas.

Las respuestas administrativas de lectura no contienen secretos. En creación, usuario y contraseña son obligatorios
para orígenes y destinos. En edición, las credenciales se envían solo si se rellenan explícitamente los dos campos.

El flujo mínimo de demo desde la UI es crear worker, origen y destino; crear una configuración con tablas; asignarla al
worker; materializar CDC para el origen; reiniciar manualmente el worker; y consultar el contrato runtime por
`WORKER_ID`. Los cambios de configuración no se aplican en caliente.

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

Desde la raíz del repositorio:

```bash
make frontend-build
```

Desde `frontend/`:

```bash
npm run build
```

## Smoke administrativo

El frontend incluye una suite smoke e2e ligera con Playwright para validar la navegación administrativa, la creación de
workers, orígenes y destinos, y una carga suave de configuraciones sin levantar Docker ni servicios externos:

Desde la raíz del repositorio:

```bash
make frontend-smoke
```

También puede ejecutarse directamente con npm desde la raíz:

```bash
npm --prefix frontend run smoke:admin
```

Desde `frontend/`:

```bash
npm run smoke:admin
```

Si `npm --prefix frontend ...` muestra una ruta terminada en `frontend/frontend/package.json`, la terminal está dentro
de `frontend/`; en ese caso usa `npm run smoke:admin` o vuelve a la raíz antes de usar `--prefix`.

`smoke:workers` se mantiene como alias compatible del smoke administrativo.

Si Chromium no está instalado en la caché local de Playwright, prepararlo una vez con:

```bash
npm --prefix frontend exec playwright install chromium
```

O, si ya estás dentro de `frontend/`:

```bash
npx playwright install chromium
```

La prueba arranca Vite con una URL de API mockeada, intercepta `GET /health`, `GET /api/v1/workers` y
las rutas administrativas mínimas, y verifica estados vacíos, modales de creación, payloads enviados y entidades
reflejadas en tablas. Es una validación acotada a Chromium y complementa `make e2e-validate`; no sustituye la demo e2e
completa del stack.

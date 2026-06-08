# cdc-sync

Sistema configurable de sincronización entre BBDD transaccionales y BBDD analíticas basado en CDC.

## Stack local

```text
PostgreSQL (OLTP) -> Debezium -> Kafka -> Worker (Python) -> ClickHouse
                      ^
                      |
FastAPI (control plane) -> PostgreSQL (control plane)
                      ^
                      |
Frontend administrativo (React)
```

El repositorio contiene la vertical local del MVP: API del control plane, consola administrativa, infraestructura CDC,
workers stateless y destino analítico ClickHouse.

La configuración local queda separada en varios contratos:

- `.env`: orquestación compartida del stack Docker.
- `frontend/.env`: variables consumidas por Vite en desarrollo local.
- `api/.env.example`: variables técnicas para ejecutar la API fuera de Docker, si se necesita.
- `worker/.env.example`: variables técnicas mínimas para ejecutar el worker fuera de Docker, si se necesita.

El conector Debezium local usa un fixture propio generado desde
`infrastructure/debezium/connectors/postgresql/source.local.env.example`; no es la fuente de verdad funcional del MVP.

## Requisitos previos

- Docker y Docker Compose
- `make`

## Inicio rápido

Después de clonar el repositorio, preparar los ficheros locales de entorno:

```bash
make env-init
```

Este paso crea, sin sobrescribir si ya existen:

- `.env`;
- `frontend/.env`;
- `infrastructure/debezium/connectors/generated/postgresql-source.local.env`.

## Consola administrativa

La ruta recomendada para levantar la consola conectada a la API local es:

```bash
make env-init
make api-migrate
make frontend-up
make api-health
```

Después, abrir:

```text
http://localhost:5173
```

Resultado esperado:

- la API responde correctamente en `http://localhost:8000`;
- la consola carga con el indicador de API operativo;
- las pestañas `Workers`, `Orígenes` y `Destinos` muestran sus listados o estados vacíos sin errores.

`make frontend-up` arranca el frontend de desarrollo con Docker Compose y levanta sus dependencias declaradas. Las
migraciones del control plane siguen siendo un paso explícito para evitar que la UI apunte a una base sin esquema.

## API REST del control plane

El backend FastAPI vive en `api/`, está desacoplado del worker y persiste la configuración administrativa en su propio
PostgreSQL.

Flujo mínimo local:

```bash
make env-init
make api-migrate
make api-up
make api-health
```

La documentación detallada del backend está en [docs/api.md](docs/api.md).

## Frontend administrativo

La base del frontend vive en `frontend/` y usa Vite, React, TypeScript y Mantine para la UI administrativa mínima del
control plane.

Flujo local con npm, útil si no se quiere usar el servicio Docker del frontend:

```bash
make env-init
make api-migrate
make api-up
make frontend-install
make frontend-dev
```

`make frontend-api-types` solo es necesario cuando cambia el contrato OpenAPI y se quieren regenerar los tipos del
frontend.

Flujo local con Docker Compose:

```bash
make env-init
make api-migrate
make frontend-up
make frontend-logs
```

El servicio está integrado en el stack local y puede arrancarse con `docker compose up frontend` o junto al resto del
stack. La documentación detallada está en [frontend/README.md](frontend/README.md).

Para demos manuales creadas desde la consola, los workers stateless pueden arrancarse por identificador operativo:

```bash
make workers-up WORKER_IDS=crm-worker,sales-worker
make workers-down WORKER_IDS=crm-worker,sales-worker
```

`workers-up` valida primero que la API publique `GET /workers/{worker_id}/config` para cada identificador. Esta
orquestación es local de demo; la API y la UI no arrancan ni paran contenedores.

## Validación end-to-end

Cuando la consola y la API ya levantan correctamente, la validación reproducible de la vertical completa se ejecuta con:

```bash
make e2e-validate
```

No hay un segundo flujo separado de demo: esta validación ejecuta la demo local multi-worker. El recorrido crea
configuración por API, materializa Debezium, arranca workers, genera cambios en PostgreSQL y valida la convergencia en
ClickHouse.

La validación usa tres workers dinámicos:

- `crm-worker`: cuentas, contactos, oportunidades y actividades.
- `sales-worker`: pedidos, líneas, facturas y pagos.
- `operations-worker`: proveedores, productos, almacenes y movimientos.

También puede ejecutarse por pasos si se desea. La documentación detallada está en
[docs/local-stack.md](docs/local-stack.md).

## Documentación detallada

- [Stack local](docs/local-stack.md)
- [PostgreSQL](docs/postgresql.md)
- [Kafka y ZooKeeper](docs/kafka.md)
- [Debezium](docs/debezium.md)
- [Worker](docs/worker.md)
- [ClickHouse](docs/clickhouse.md)
- [API REST](docs/api.md)
- [Modelo del control plane](docs/control-plane-model.md)

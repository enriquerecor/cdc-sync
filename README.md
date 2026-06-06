# cdc-sync

Sistema configurable de sincronización entre BBDD transaccionales y BBDD analíticas basado en CDC.

## Stack local

```text
PostgreSQL (OLTP) -> Debezium -> Kafka -> Worker (Python) -> ClickHouse
                      ^
                      |
FastAPI (control plane) -> PostgreSQL (control plane)
```

Esta fase deja levantada la infraestructura base y valida la persistencia versionada extremo a extremo desde
PostgreSQL hasta ClickHouse para las tablas configuradas en el worker.

La configuración local queda separada en tres contratos:

- `.env`: orquestación compartida del stack Docker.
- `api/.env.example`: variables técnicas para ejecutar la API fuera de Docker.
- `worker/.env.example`: variables técnicas del worker y fixtures temporales hasta la carga remota de #28.

El conector Debezium local usa un fixture propio generado desde
`infrastructure/debezium/connectors/postgresql/source.local.env.example`; no es la fuente de verdad funcional del MVP.

## Requisitos previos

- Docker y Docker Compose
- `make`

## Inicio rápido

Preparar los ficheros locales de entorno:

```bash
make env-init
```

Este paso crea `.env` y `worker/config/tables.json` a partir de sus ejemplos versionados si todavía no existen.
También crea el fixture local del conector en `infrastructure/debezium/connectors/generated/`.

## API REST del control plane

La milestone `API REST` introduce un backend FastAPI desacoplado del worker y con persistencia propia en PostgreSQL.

Flujo mínimo local:

```bash
make env-init
make api-up
make api-migrate
make api-health
```

La documentación detallada del backend está en [docs/api.md](docs/api.md).

Ejecutar la validación e2e reproducible:

```bash
make e2e-validate
```

Este comando:

- levanta el stack con `docker compose`
- aplica el conector Debezium
- ejecuta una validación completa sobre `customers` y `orders`
- comprueba en ClickHouse los casos de `INSERT`, `UPDATE` y `DELETE` lógico
- termina con error si alguna comprobación no converge dentro del timeout

## Qué incluye esta fase

- PostgreSQL local con tablas de prueba `customers` y `orders`
- ZooKeeper y Kafka para mensajería
- Debezium Connect con conector PostgreSQL configurable
- Worker base en Python que consume eventos CDC, los normaliza y los persiste en ClickHouse
- ClickHouse como primer destino analítico versionado del pipeline

Hasta que las issues #27 y #28 completen la materialización y la carga runtime desde el control plane,
`worker/config/tables.json` y el env local del conector se mantienen solo como fixtures de desarrollo.

## Documentación detallada

- [Stack local](docs/local-stack.md)
- [PostgreSQL](docs/postgresql.md)
- [Kafka y ZooKeeper](docs/kafka.md)
- [Debezium](docs/debezium.md)
- [Worker](docs/worker.md)
- [ClickHouse](docs/clickhouse.md)
- [API REST](docs/api.md)

## Estado actual

- El alta del conector CDC no se hace automáticamente con `docker compose up`.
- El flujo recomendado y soportado para esta fase es:

```bash
make e2e-validate
```

- El flujo manual con `docker compose`, `make debezium-postgres-apply` y consultas directas sigue disponible para depuración.

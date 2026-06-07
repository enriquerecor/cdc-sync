# cdc-sync

Sistema configurable de sincronización entre BBDD transaccionales y BBDD analíticas basado en CDC.

## Stack local

```text
PostgreSQL (OLTP) -> Debezium -> Kafka -> Worker (Python) -> ClickHouse
                      ^
                      |
FastAPI (control plane) -> PostgreSQL (control plane)
```

Esta fase deja levantada la infraestructura base y conecta el worker stateless con el contrato runtime publicado por el
control plane.

La configuración local queda separada en tres contratos:

- `.env`: orquestación compartida del stack Docker.
- `api/.env.example`: variables técnicas para ejecutar la API fuera de Docker.
- `worker/.env.example`: variables técnicas mínimas para ejecutar el worker fuera de Docker.

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

Este paso crea `.env` si todavía no existe. También crea el fixture local del conector en
`infrastructure/debezium/connectors/generated/`.

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

La validación e2e anterior queda obsoleta temporalmente:

```bash
make e2e-validate
```

Este comando falla de forma explícita porque dependía del fixture JSON local eliminado en #28. La demo reproducible
multi-worker desde configuración API queda delegada a #33.

## Qué incluye esta fase

- PostgreSQL local con tablas de prueba `customers` y `orders`
- ZooKeeper y Kafka para mensajería
- Debezium Connect con conector PostgreSQL materializable desde el control plane
- Worker stateless en Python que carga su configuración runtime desde la API, consume eventos CDC, los normaliza y los
  persiste en ClickHouse
- ClickHouse como primer destino analítico versionado del pipeline

El worker no usa JSON local de tablas ni variables locales de Kafka o ClickHouse como fuente funcional. El env local del
conector se conserva como fixture de depuración local, pero no como fuente canónica del MVP.

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
- El flujo e2e completo queda pendiente de #33. Hasta entonces, este comando falla con un mensaje explícito:

```bash
make e2e-validate
```

- El flujo manual con `docker compose`, `make debezium-postgres-apply` y consultas directas sigue disponible para depuración.

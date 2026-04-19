# cdc-sync

Sistema configurable de sincronización entre BBDD transaccionales y BBDD analíticas basado en CDC.

## Stack local

```text
PostgreSQL -> Debezium -> Kafka -> Worker (Python) -> ClickHouse
```

Esta fase deja levantada la infraestructura base y valida la persistencia versionada extremo a extremo desde
PostgreSQL hasta ClickHouse para las tablas configuradas en el worker.

## Requisitos previos

- Docker y Docker Compose
- `make`

## Inicio rápido

Preparar los ficheros locales de entorno:

```bash
make env-init
```

Este paso crea `.env` y `worker/config/tables.json` a partir de sus ejemplos versionados si todavia no existen.

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

## Documentación detallada

- [Stack local](docs/local-stack.md)
- [PostgreSQL](docs/postgresql.md)
- [Kafka y ZooKeeper](docs/kafka.md)
- [Debezium](docs/debezium.md)
- [Worker](docs/worker.md)
- [ClickHouse](docs/clickhouse.md)

## Estado actual

- El alta del conector CDC no se hace automáticamente con `docker compose up`.
- El flujo recomendado y soportado para esta fase es:

```bash
make e2e-validate
```

- El flujo manual con `docker compose`, `make debezium-postgres-apply` y consultas directas sigue disponible para depuración.

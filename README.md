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

Levantar toda la infraestructura:

```bash
docker compose up -d --build
```

Registrar el conector CDC:

```bash
make debezium-postgres-apply
make debezium-postgres-status
```

## Validación rápida

En una terminal, seguir los logs del worker:

```bash
docker compose logs -f worker
```

En otra terminal, insertar una fila en PostgreSQL:

```bash
docker compose exec postgres psql -U cdc_sync -d cdc_sync -c \
  "INSERT INTO customers (email, full_name) VALUES ('quick-start@example.com', 'Quick Start Customer');"
```

Resultado esperado:

- Debezium publica el evento en Kafka.
- El worker crea la base y las tablas analíticas en ClickHouse si no existen.
- La fila insertada aparece en `cdc_sync_analytics.customers`.

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
- El flujo soportado y documentado para esta fase es:

```bash
docker compose up -d --build
make debezium-postgres-apply
```

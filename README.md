# cdc-sync

Sistema configurable de sincronización entre BBDD transaccionales y BBDD analíticas basado en CDC.

## Stack local

```text
PostgreSQL -> Debezium -> Kafka -> Worker (Python) -> ClickHouse
```

Esta fase deja levantada la infraestructura base y valida la conectividad extremo a extremo. No incluye todavía
transformación de eventos, inserción en ClickHouse ni lógica de versionado.

## Requisitos previos

- Docker y Docker Compose
- `make`

## Inicio rápido

Preparar el fichero local de entorno:

```bash
make env-init
```

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
- El worker imprime una línea `cdc_event` en logs con `quick-start@example.com`.

## Qué incluye esta fase

- PostgreSQL local con tablas de prueba `customers` y `orders`
- ZooKeeper y Kafka para mensajería
- Debezium Connect con conector PostgreSQL configurable
- Worker base en Python que consume eventos CDC y los escribe en logs
- ClickHouse base como destino analítico futuro

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

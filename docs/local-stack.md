# Stack local

## Objetivo

Levantar un entorno reproducible para validar el flujo:

```text
PostgreSQL -> Debezium -> Kafka -> Worker -> ClickHouse
```

## Requisitos previos

- Docker y Docker Compose
- `make`

## Arranque completo

Preparar el entorno local:

```bash
make env-init
```

Ejecutar la validación e2e reproducible:

```bash
make e2e-validate
```

Este flujo automatiza:

- el arranque del stack completo con `docker compose up -d --build`
- el alta del conector PostgreSQL en Kafka Connect
- la validación del flujo `customers` y `orders`
- las comprobaciones en ClickHouse de `INSERT`, `UPDATE` y `DELETE` lógico

## Reset global

Si se quiere reconstruir el proyecto desde cero:

```bash
docker compose down -v
make e2e-validate
```

## Diagnóstico manual

Si se necesita inspeccionar el stack paso a paso:

```bash
docker compose logs -f worker
make debezium-postgres-status
```

## Documentación por bloque

- [PostgreSQL](postgresql.md)
- [Kafka y ZooKeeper](kafka.md)
- [Debezium](debezium.md)
- [Worker](worker.md)
- [ClickHouse](clickhouse.md)

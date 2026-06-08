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

Este comando crea, sin sobrescribir si ya existen:

- `.env`, con variables compartidas por Docker Compose;
- `infrastructure/debezium/connectors/generated/postgresql-source.local.env`, fixture temporal del conector Debezium.

La configuración funcional del MVP vive en el control plane. El fixture del conector sigue disponible para depuración
local, pero el worker ya no usa JSON local como fuente de verdad.

La validación e2e anterior queda obsoleta temporalmente:

```bash
make e2e-validate
```

El comando falla de forma explícita porque dependía del fixture JSON local eliminado en #28. La demo reproducible
multi-worker desde configuración API queda delegada a #33.

## Reset global

Si se quiere reconstruir el proyecto desde cero:

```bash
docker compose down -v
make env-init
```

## Diagnóstico manual

Si se necesita inspeccionar el stack paso a paso:

```bash
docker compose logs -f worker
make debezium-postgres-status
```

## Contratos de entorno

- API en Docker: recibe `API_*` desde `docker-compose.yml` y la conexión interna al PostgreSQL del control plane.
- Worker en Docker: arranca con `WORKER_ID` y `WORKER_CONTROL_PLANE_BASE_URL`; Kafka, tablas y ClickHouse vienen del contrato runtime remoto.
- Infraestructura local: PostgreSQL, Kafka, Connect y ClickHouse toman sus puertos y credenciales de `.env`.

## Documentación por bloque

- [PostgreSQL](postgresql.md)
- [Kafka y ZooKeeper](kafka.md)
- [Debezium](debezium.md)
- [Worker](worker.md)
- [ClickHouse](clickhouse.md)

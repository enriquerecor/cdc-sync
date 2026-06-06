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
- `worker/config/tables.json`, fixture temporal del worker local;
- `infrastructure/debezium/connectors/generated/postgresql-source.local.env`, fixture temporal del conector Debezium.

La configuración funcional del MVP debe vivir en el control plane. El fixture del conector sigue alimentando la
validación e2e actual y la depuración local; el JSON del worker mantiene operativa la demo local hasta completar la
carga remota del worker.

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

## Contratos de entorno

- API en Docker: recibe `API_*` desde `docker-compose.yml` y la conexión interna al PostgreSQL del control plane.
- Worker en Docker: arranca con `WORKER_ID` y `WORKER_CONTROL_PLANE_BASE_URL`; el JSON local y ClickHouse por entorno son compatibilidad temporal.
- Infraestructura local: PostgreSQL, Kafka, Connect y ClickHouse toman sus puertos y credenciales de `.env`.

## Documentación por bloque

- [PostgreSQL](postgresql.md)
- [Kafka y ZooKeeper](kafka.md)
- [Debezium](debezium.md)
- [Worker](worker.md)
- [ClickHouse](clickhouse.md)

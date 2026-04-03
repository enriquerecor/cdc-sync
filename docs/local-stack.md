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

Levantar la infraestructura:

```bash
docker compose up -d --build
```

Registrar el conector CDC:

```bash
make debezium-postgres-apply
make debezium-postgres-status
```

## Comprobación rápida

Seguir los logs del worker:

```bash
docker compose logs -f worker
```

Insertar una fila de prueba:

```bash
docker compose exec postgres psql -U cdc_sync -d cdc_sync -c \
  "INSERT INTO customers (email, full_name) VALUES ('local-stack-check@example.com', 'Local Stack Check');"
```

Resultado esperado:

- el conector Debezium permanece en `RUNNING`
- aparece un evento en Kafka para `cdc_sync.public.customers`
- el worker escribe una línea `cdc_event` con el `email` insertado

## Reset global

Si se quiere reconstruir el proyecto desde cero:

```bash
docker compose down -v
docker compose up -d --build
make debezium-postgres-apply
```

## Documentación por bloque

- [PostgreSQL](postgresql.md)
- [Kafka y ZooKeeper](kafka.md)
- [Debezium](debezium.md)
- [Worker](worker.md)
- [ClickHouse](clickhouse.md)

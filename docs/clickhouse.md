# ClickHouse

## Alcance en esta fase

- servicio base del destino analítico
- tablas de destino creadas por el worker al arranque
- escrituras versionadas desde el worker

## Arranque

```bash
docker compose up -d clickhouse
```

Puertos por defecto:

- HTTP: `localhost:8123`
- protocolo nativo: `localhost:9000`

Base usada por el worker:

- `cdc_sync_analytics`

## Validaciones

Comprobar estado:

```bash
docker compose ps
```

Consultar versión:

```bash
docker compose exec clickhouse clickhouse-client --query "SELECT version()"
```

Listar bases:

```bash
docker compose exec clickhouse clickhouse-client --query "SHOW DATABASES"
```

Resultado esperado:

- aparece `cdc_sync_analytics`

Listar tablas creadas por el worker:

```bash
docker compose exec clickhouse clickhouse-client --query "SHOW TABLES FROM cdc_sync_analytics"
```

Resultado esperado:

- aparecen `customers` y `orders` si ambas tablas estan habilitadas en `worker/config/tables.json`

## Recreación del servicio

```bash
docker compose stop clickhouse
docker compose rm -f clickhouse
docker compose up -d clickhouse
```

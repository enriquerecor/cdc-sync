# ClickHouse

## Alcance en esta fase

- servicio base del destino analítico
- sin tablas de destino
- sin escrituras desde el worker

## Arranque

```bash
docker compose up -d clickhouse
```

Puertos por defecto:

- HTTP: `localhost:8123`
- protocolo nativo: `localhost:9000`

Base inicial:

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

## Recreación del servicio

```bash
docker compose stop clickhouse
docker compose rm -f clickhouse
docker compose up -d clickhouse
```

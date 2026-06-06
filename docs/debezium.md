# Debezium

## Alcance en esta fase

- servicio base de Kafka Connect con imagen de Debezium
- conector PostgreSQL configurable por plantilla
- captura de cambios de `public.customers` y `public.orders`

## Arranque de Connect

```bash
docker compose up -d connect
```

API REST por defecto:

- `http://localhost:8083`

## Validaciones del servicio

Comprobar raíz de la API:

```bash
curl -fsS http://localhost:8083/
```

Comprobar plugins disponibles:

```bash
curl -fsS http://localhost:8083/connector-plugins
```

## Flujo del conector PostgreSQL

La plantilla versionada está en:

```bash
infrastructure/debezium/connectors/postgresql/source.config.template.json
```

Las variables locales del conector viven en:

```bash
infrastructure/debezium/connectors/generated/postgresql-source.local.env
```

`make env-init` lo crea desde `infrastructure/debezium/connectors/postgresql/source.local.env.example`.
Es un fixture temporal para el stack local; la materialización desde el control plane queda para #27.

Renderizar configuración local:

```bash
make debezium-postgres-render
```

Aplicar configuración:

```bash
make debezium-postgres-apply
```

Consultar estado:

```bash
make debezium-postgres-status
```

Resultado esperado:

- el conector `postgres-cdc-source` queda en `RUNNING`

## Validación CDC en Kafka

Insertar una fila en `customers`:

```bash
docker compose exec postgres psql -U cdc_sync -d cdc_sync -c \
  "INSERT INTO customers (email, full_name) VALUES ('cdc-check@example.com', 'CDC Check Customer');"
```

Consumir el topic CDC:

```bash
docker compose exec kafka kafka-console-consumer \
  --topic cdc_sync.public.customers \
  --bootstrap-server kafka:29092 \
  --from-beginning \
  --timeout-ms 15000
```

Insertar una fila en `orders`:

```bash
docker compose exec postgres psql -U cdc_sync -d cdc_sync -c \
  "INSERT INTO orders (customer_id, order_number, total_amount, status) VALUES ((SELECT id FROM customers WHERE email = 'cdc-check@example.com'), 'CDC-CHECK-ORDER', 123.45, 'created');"
```

Consumir el topic de `orders`:

```bash
docker compose exec kafka kafka-console-consumer \
  --topic cdc_sync.public.orders \
  --bootstrap-server kafka:29092 \
  --from-beginning \
  --timeout-ms 15000
```

## Nota sobre snapshot y streaming

En un arranque limpio del conector:

- pueden aparecer eventos con `op: "r"` durante el snapshot inicial
- las inserciones posteriores se reciben con `op: "c"` en streaming

Si se quiere comprobar solo streaming, arrancar primero el consumidor sin `--from-beginning` y luego insertar la fila.

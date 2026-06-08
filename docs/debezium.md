# Debezium

## Alcance en esta fase

- servicio base de Kafka Connect con imagen de Debezium
- materialización canónica desde el control plane mediante adapter Debezium PostgreSQL
- conector PostgreSQL configurable por plantilla solo como fixture local de depuración
- captura de cambios de las tablas habilitadas en las configuraciones del control plane

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

## Flujo desde el control plane

La forma canónica de crear o actualizar conectores CDC en el MVP es llamar a la API administrativa del control plane:

```bash
curl -fsS -X PUT \
  http://localhost:8000/api/v1/source-connections/<source_connection_id>/cdc-connector
```

La API:

- lee la conexión de origen y sus credenciales desde PostgreSQL del control plane;
- selecciona un compilador por `source_type`;
- usa `DebeziumPostgresConnectorCompiler` para `source_type = postgresql`;
- une las tablas habilitadas de configs habilitadas que usan ese origen;
- aplica la configuración en Kafka Connect con `PUT /connectors/<name>/config`.

En la demo multi-worker, esa unión incluye las tablas ERP/CRM asignadas a `crm-worker`, `sales-worker` y
`operations-worker`.

PostgreSQL es el primer adapter Debezium implementado, no una dependencia del caso de uso. En futuras fases se podrán
añadir compiladores para MySQL u otros orígenes OLTP sin cambiar el flujo administrativo.

## Fixture local del conector PostgreSQL

La plantilla versionada está en:

```bash
infrastructure/debezium/connectors/postgresql/source.config.template.json
```

Las variables locales del conector viven en:

```bash
infrastructure/debezium/connectors/generated/postgresql-source.local.env
```

`make env-init` lo crea desde `infrastructure/debezium/connectors/postgresql/source.local.env.example`.
Es un fixture temporal para la validación e2e actual y para depuración local; no es la fuente de verdad funcional del
MVP.

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

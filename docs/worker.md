# Worker

## Alcance en esta fase

- consumidor base en Python
- suscripción a los topics CDC de `customers` y `orders`
- logging de eventos recibidos

## Arranque

Preparar la configuracion local del worker:

```bash
make env-init
```

Esto crea `worker/config/tables.json` a partir de `worker/config/tables.example.json` si todavia no existe.

El fichero real de configuracion del entorno no se versiona. El ejemplo versionado define el contrato base esperado
por el worker.

Contrato minimo actual por tabla:

- `enabled`
- `source.connection`
- `source.schema` (opcional)
- `source.table`
- `source.topic`
- `pk`
- `sync.mode`

Arrancar el servicio:

```bash
docker compose up -d --build worker
```

Topics por defecto:

- `cdc_sync.public.customers`
- `cdc_sync.public.orders`

Los topics se derivan del fichero de tablas mediante `source.topic`.
La ruta del fichero de tablas se configura mediante `WORKER_TABLE_CONFIG_PATH` en `.env`.

## Validaciones

Comprobar que el servicio está levantado:

```bash
docker compose ps
```

Seguir logs:

```bash
docker compose logs -f worker
```

Resultado esperado al arrancar:

- aparece una línea `worker_started`

## Tests

> Este flujo usa `.venv` y `worker/requirements-dev.txt`, y no modifica la imagen runtime del worker.

Preparar el entorno virtual local del repo con las dependencias de desarrollo del worker:

```bash
make worker-test-deps
```

Ejecutar la suite de tests del worker:

```bash
make worker-test
```

## Validación de consumo

Registrar el conector si el stack se ha levantado desde cero:

```bash
make debezium-postgres-apply
make debezium-postgres-status
```

Insertar una fila en `customers`:

```bash
docker compose exec postgres psql -U cdc_sync -d cdc_sync -c \
  "INSERT INTO customers (email, full_name) VALUES ('worker-check@example.com', 'Worker Check Customer');"
```

Resultado esperado:

- el worker escribe una línea `cdc_event` para `cdc_sync.public.customers`

Validar también `orders`:

```bash
docker compose exec postgres psql -U cdc_sync -d cdc_sync -c \
  "INSERT INTO orders (customer_id, order_number, total_amount, status) VALUES ((SELECT id FROM customers WHERE email = 'worker-check@example.com'), 'WORKER-CHECK-ORDER', 44.90, 'created');"
```

Resultado esperado:

- aparece una segunda línea `cdc_event` para `cdc_sync.public.orders`

## Nota sobre offsets

En el primer arranque del grupo `cdc-sync-worker`, la estrategia `earliest` puede reproducir primero eventos
históricos del topic. Para validar el evento nuevo, buscar en logs el valor insertado.

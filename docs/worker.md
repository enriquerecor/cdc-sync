# Worker

## Alcance en esta fase

- consumidor base en Python
- suscripción a los topics CDC de `customers` y `orders`
- logging de eventos recibidos

## Arranque

```bash
docker compose up -d --build worker
```

Topics por defecto:

- `cdc_sync.public.customers`
- `cdc_sync.public.orders`

La lista se configura mediante `WORKER_KAFKA_TOPICS` en `.env`.

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

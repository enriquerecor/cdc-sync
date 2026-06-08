# PostgreSQL

## Alcance en esta fase

- base `cdc_sync`
- tablas de prueba `customers` y `orders`
- fixture ERP/CRM para demo multi-worker:
  - CRM: `crm_accounts`, `crm_contacts`, `crm_opportunities`, `crm_activities`
  - ventas: `sales_orders`, `sales_order_lines`, `sales_invoices`, `sales_payments`
  - operaciones: `ops_suppliers`, `ops_products`, `ops_warehouses`, `ops_inventory_movements`
- datos semilla
- soporte para CDC con `wal_level=logical`

## Arranque

```bash
docker compose up -d postgres
```

Credenciales por defecto:

- base de datos: `cdc_sync`
- usuario: `cdc_sync`
- contraseña: `cdc_sync`

## Validaciones

Comprobar tablas:

```bash
docker compose exec postgres psql -U cdc_sync -d cdc_sync -c "\\dt"
```

Consultar seeds:

```bash
docker compose exec postgres psql -U cdc_sync -d cdc_sync -c "SELECT * FROM customers;"
docker compose exec postgres psql -U cdc_sync -d cdc_sync -c "SELECT * FROM orders;"
docker compose exec postgres psql -U cdc_sync -d cdc_sync -c "SELECT * FROM crm_accounts;"
docker compose exec postgres psql -U cdc_sync -d cdc_sync -c "SELECT * FROM ops_products;"
docker compose exec postgres psql -U cdc_sync -d cdc_sync -c "SELECT * FROM sales_orders;"
```

Comprobar soporte CDC:

```bash
docker compose exec postgres psql -U cdc_sync -d cdc_sync -c "SHOW wal_level;"
```

Resultado esperado:

- existen `customers`, `orders` y las tablas ERP/CRM de demo
- `wal_level` devuelve `logical`

## Demo ERP/CRM

Los scripts `003-erp-crm-schema.sql` y `004-erp-crm-seed.sql` forman el origen OLTP usado por `make demo-local`.
El runner de demo vuelve a aplicarlos de forma idempotente durante `make demo-up`, para que también funcionen en
volúmenes locales ya creados.

Las filas generadas por el paso `make demo-changes` usan claves naturales con prefijo `DEMO-E2E-`. Antes de insertar
los cambios de una nueva ejecución, el runner elimina solo esas filas de demo en orden seguro de claves foráneas.

## Reset del servicio

Los scripts de inicialización solo se ejecutan cuando el volumen está vacío.

```bash
docker compose down -v
docker compose up -d postgres
```

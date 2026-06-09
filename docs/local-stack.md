# Stack local

## Objetivo

Levantar un entorno reproducible para validar el flujo:

```text
PostgreSQL -> Debezium -> Kafka -> Worker -> ClickHouse
                     ^
                     |
             API + frontend administrativo
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
- `frontend/.env`, con la URL de la API consumida por Vite;
- `infrastructure/debezium/connectors/generated/postgresql-source.local.env`, fixture temporal del conector Debezium.

La configuración funcional del MVP vive en el control plane. El fixture del conector sigue disponible para depuración
local, pero el worker ya no usa JSON local como fuente de verdad.

## Consola administrativa

Para levantar la UI conectada a la API local desde cero:

```bash
make env-init
make api-migrate
make frontend-up
make api-health
```

Abrir:

```text
http://localhost:5173
```

La consola permite gestionar workers, conexiones de origen y destinos analíticos. Las configuraciones de tablas y
asignaciones efectivas forman parte de la API y de la demo e2e, pero la pestaña de configuraciones sigue como
placeholder de la siguiente fase de UI.

## Demo end-to-end

La demo e2e oficial valida la vertical completa multi-worker desde configuración API:

```bash
make demo-local
```

`make e2e-validate` delega en el mismo flujo.

La demo crea por API el origen PostgreSQL, el destino ClickHouse, tres workers, tres configuraciones y sus asignaciones
efectivas. Después materializa Debezium desde el control plane, arranca workers stateless con `WORKER_ID`, aplica
cambios en PostgreSQL y reconcilia ClickHouse con `SELECT ... FINAL`.

## Demo paso a paso

Si se quiere inspeccionar o depurar el flujo por fases:

```bash
make demo-up
make demo-migrate
make demo-configure
make demo-materialize
make demo-workers
make demo-changes
make demo-assert
```

Cada paso falla de forma explícita si falta una dependencia previa. Los identificadores creados por la API se guardan en
`.tmp/e2e-demo-state.json`.

## Workers de demo

Por defecto se usan tres workers, definidos con `DEMO_WORKER_IDS`:

```bash
DEMO_WORKER_IDS=crm-worker,sales-worker,operations-worker
```

Mapa funcional:

- `crm-worker`: `crm_accounts`, `crm_contacts`, `crm_opportunities`, `crm_activities`.
- `sales-worker`: `sales_orders`, `sales_order_lines`, `sales_invoices`, `sales_payments`.
- `operations-worker`: `ops_suppliers`, `ops_products`, `ops_warehouses`, `ops_inventory_movements`.

El runner arranca un contenedor por worker con `docker compose run -d --no-deps -e WORKER_ID=... worker`. Esto es
orquestación local de demo; no implica autoescalado ni gestión de ciclo de vida desde el control plane.

## Qué valida la demo

- API: creación de origen, destino, workers, configuraciones y asignaciones efectivas.
- Kafka Connect: materialización idempotente del conector Debezium desde la API.
- Worker runtime: cada proceso carga `GET /workers/{id}/config` al arrancar y usa un `group_id` propio.
- PostgreSQL/ClickHouse: todas las tablas configuradas reciben `INSERT`, `UPDATE` y `DELETE`.
- Reconciliación: `SELECT ... FINAL WHERE deleted = 0` coincide con PostgreSQL para las columnas configuradas.
- Lápidas: `SELECT ... FINAL WHERE deleted = 1` contiene las claves primarias borradas esperadas.

En este MVP, `deleted = 1` representa una lápida por clave primaria. No se interpreta como una copia completa obligatoria
de la fila previa al borrado.

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

Los workers de la demo usan nombres de contenedor estables:

```bash
docker logs -f cdc-sync-demo-worker-crm-worker
docker logs -f cdc-sync-demo-worker-sales-worker
docker logs -f cdc-sync-demo-worker-operations-worker
```

## Contratos de entorno

- API en Docker: recibe `API_*` desde `docker-compose.yml` y la conexión interna al PostgreSQL del control plane.
- Worker en Docker: arranca con `WORKER_ID` y `WORKER_CONTROL_PLANE_BASE_URL`; Kafka, tablas y ClickHouse vienen del contrato runtime remoto.
- Infraestructura local: PostgreSQL, Kafka, Connect y ClickHouse toman sus puertos y credenciales de `.env`.
- Los cambios de configuración hechos por la API requieren reiniciar manualmente el worker para surtir efecto.

## Documentación por bloque

- [PostgreSQL](postgresql.md)
- [Kafka y ZooKeeper](kafka.md)
- [Debezium](debezium.md)
- [Worker](worker.md)
- [ClickHouse](clickhouse.md)
- [API REST](api.md)
- [Modelo del control plane](control-plane-model.md)

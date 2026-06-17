# Demo industrial OLTP -> CDC -> OLAP

Esta demo ejecuta el recorrido completo con el esquema `industrial_analytics`:

PostgreSQL OLTP -> Debezium -> Kafka -> workers -> ClickHouse OLAP.

La configuración CDC se crea desde la API del control plane. La materialización
del conector Debezium puede hacerse desde la interfaz durante la defensa o con
el target alternativo de Make.

## Tamaños disponibles

- `analytics-demo-dataset-small`: validación rápida.
- `analytics-demo-dataset-defense`: tamaño recomendado para defensa.
- `analytics-demo-dataset-medium`: prueba pesada.

El tamaño de defensa usa `medium` con escala reducida (`0.03`) para mantener el
dataset analítico real sin forzar tanto el snapshot.

## Recorrido recomendado para defensa

```bash
make analytics-demo-reset
make analytics-demo-up
make analytics-demo-dataset-defense
make analytics-demo-configure
```

En este punto el control plane contiene:

- `industrial-sales-worker`: `clientes`, `productos`, `pedidos`, `lineas_pedido`.
- `industrial-production-worker`: `maquinas`, `ordenes_produccion`, `lecturas_sensores`.
- `industrial-quality-worker`: `proveedores`, `materiales`, `lotes_material`, `consumos_material`, `no_conformidades`.

## Materialización CDC desde la UI

Abrir la consola administrativa:

```text
http://localhost:5173
```

Materializar el conector Debezium desde la sección de configuraciones.

## Alternativa por terminal

```bash
make analytics-demo-materialize
```

## Snapshot inicial

```bash
make analytics-demo-workers
make analytics-demo-wait-snapshot
make analytics-demo-benchmark
```

`analytics-demo-wait-snapshot` comprueba que ClickHouse, los tres workers y el
conector Debezium siguen en ejecución. Si alguno cae, el comando falla con la
causa antes de agotar el timeout. Mientras espera, imprime progreso periódico
con filas vivas en ClickHouse frente a PostgreSQL y las tablas que aún no han
convergido.

El benchmark muestra por consulta:

- fase;
- motor;
- tiempo;
- filas;
- firma lógica.

PostgreSQL y ClickHouse deben devolver las mismas filas y la misma firma.

## Cambios CDC

```bash
make analytics-demo-changes
make analytics-demo-wait-cdc
make analytics-demo-benchmark-after
```

La tanda CDC aplica inserts, updates y deletes. Después, las firmas deben haber
cambiado respecto al snapshot inicial y volver a coincidir entre PostgreSQL y
ClickHouse.

## Validación rápida

Para comprobar el flujo sin preparar una demo completa:

```bash
make analytics-demo-reset
make analytics-demo-up
make analytics-demo-dataset-small
make analytics-demo-configure
make analytics-demo-materialize
make analytics-demo-workers
make analytics-demo-wait-snapshot
make analytics-demo-benchmark
make analytics-demo-changes
make analytics-demo-wait-cdc
make analytics-demo-benchmark-after
```

## Prueba pesada

```bash
make analytics-demo-reset
make analytics-demo-up
make analytics-demo-dataset-medium
make analytics-demo-configure
make analytics-demo-materialize
make analytics-demo-workers
make analytics-demo-wait-snapshot
make analytics-demo-benchmark
make analytics-demo-changes
make analytics-demo-wait-cdc
make analytics-demo-benchmark-after
```

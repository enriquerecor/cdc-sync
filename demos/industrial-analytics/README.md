# Dataset industrial analítico

Dataset sintético y determinista para una demostración analítica separada del recorrido `demo-*` actual. Carga un ERP
industrial ficticio en PostgreSQL dentro del esquema `industrial_analytics` y deja preparadas cinco consultas pesadas
para medir tiempos aproximados en PostgreSQL antes de conectarlo a ClickHouse o al flujo CDC.

## Alcance

- No configura Debezium, workers ni ClickHouse.
- No modifica el recorrido `make demo-local` ni `make e2e-validate`.
- Recrea solo el esquema indicado con `--schema`; por defecto, `industrial_analytics`.
- Usa datos reproducibles con semilla fija y carga por `COPY FROM STDIN`.

Las columnas generadas usan dominios compatibles con estos tipos de ClickHouse: `UInt64`, `UInt8`, `String`,
`DateTime64(3, 'UTC')`, `Decimal(10, 2)` y `Decimal(12, 2)`.

## Generar y cargar

Desde la raíz del repositorio:

```bash
make analytics-dataset-load ANALYTICS_DATASET_SIZE=small
```

Tamaños disponibles:

- `small`: validación rápida.
- `medium`: volumen equivalente al primer tamaño grande de la demo.
- `large`: volumen mayor para forzar consultas de varios segundos en una demo local.

También se puede ejecutar directamente:

```bash
python3 demos/industrial-analytics/industrial_analytics_dataset.py load --size small
```

Parámetros útiles:

```bash
python3 demos/industrial-analytics/industrial_analytics_dataset.py load \
  --size medium \
  --scale 0.5 \
  --pedidos 20000 \
  --lecturas-por-orden 12
```

## Ejecutar benchmark en PostgreSQL

```bash
make analytics-dataset-benchmark
```

El comando ejecuta las queries de `benchmark_queries.sql` y muestra tiempo aproximado y número de filas devueltas. Para
probar otro término textual:

```bash
make analytics-dataset-benchmark ANALYTICS_DATASET_TERM=aceite
```

Comando completo de carga y benchmark con el tamaño por defecto:

```bash
make analytics-dataset-demo
```

## Ficheros

- `schema.sql`: creación del esquema y tablas.
- `indexes.sql`: índices mínimos para claves de unión y fechas principales.
- `benchmark_queries.sql`: consultas analíticas preparadas.
- `industrial_analytics_dataset.py`: generación determinista, carga por `COPY` y runner simple de benchmark.

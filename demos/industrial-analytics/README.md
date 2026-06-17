# Dataset industrial analítico

Dataset sintético y determinista para una demostración basada en un ERP industrial ficticio en PostgreSQL
dentro del esquema llamado `industrial_analytics`. Incluye cinco consultas analísticas de ejemplo
para medir tiempos aproximados en PostgreSQL.

Comando completo de carga y benchmark con el tamaño por defecto:

```bash
make analytics-dataset-demo
```

## Generar y cargar

Desde la raíz del repositorio:

```bash
make analytics-dataset-load ANALYTICS_DATASET_SIZE=medium
```

Tamaños disponibles:

- `small`: validación rápida.
- `medium`: volumen equivalente al primer tamaño grande de la demo.
- `large`: volumen mayor para forzar consultas de varios segundos en una demo local.

## Ejecutar benchmark en PostgreSQL

```bash
make analytics-dataset-benchmark
```

El comando ejecuta las queries de `benchmark_queries.sql` y muestra tiempo aproximado, número de filas devueltas y un
hash del resultado, para identificar cambios en el dataset posteriormente.

## Aplicar cambios para CDC

Para simular una tanda de cambios transaccionales sobre el ERP industrial:

```bash
make analytics-dataset-changes
```

El comando intercala operaciones y aplica exactamente:

- `1000` filas borradas.
- `2000` filas actualizadas, incluyendo un subconjunto actualizado más de una vez.
- `500` filas insertadas.

Después se puede repetir el benchmark para observar diferencias. Todos los hash deben ser diferentes:

```bash
make analytics-dataset-benchmark
```

## Ficheros

- `schema.sql`: creación del esquema y tablas.
- `indexes.sql`: índices mínimos para claves de unión y fechas principales.
- `cdc_changes.sql`: tanda transaccional de cambios para una futura demo CDC.
- `benchmark_queries.sql`: consultas analíticas preparadas.
- `industrial_analytics_dataset.py`: generación determinista, carga por `COPY` y runner simple de benchmark.

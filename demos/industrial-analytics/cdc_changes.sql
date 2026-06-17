\set ON_ERROR_STOP on

BEGIN;

CREATE TEMP TABLE cdc_demo_counts
(
    step_order    INTEGER NOT NULL,
    operation     TEXT    NOT NULL,
    target_table  TEXT    NOT NULL,
    affected_rows BIGINT  NOT NULL
) ON COMMIT DROP;

CREATE TEMP TABLE cdc_demo_inserted_pedidos
(
    id BIGINT PRIMARY KEY
) ON COMMIT DROP;

CREATE TEMP TABLE cdc_demo_inserted_productos
(
    id BIGINT PRIMARY KEY
) ON COMMIT DROP;

CREATE TEMP TABLE cdc_demo_updated_lineas
(
    id BIGINT PRIMARY KEY
) ON COMMIT DROP;

CREATE OR REPLACE FUNCTION pg_temp.assert_min_rows(actual BIGINT, expected BIGINT, label TEXT)
RETURNS VOID AS $$
BEGIN
    IF actual < expected THEN
        RAISE EXCEPTION '% requiere al menos % filas y solo hay %', label, expected, actual;
    END IF;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION pg_temp.assert_exact_rows(actual BIGINT, expected BIGINT, label TEXT)
RETURNS VOID AS $$
BEGIN
    IF actual <> expected THEN
        RAISE EXCEPTION '% esperaba % filas afectadas y obtuvo %', label, expected, actual;
    END IF;
END;
$$ LANGUAGE plpgsql;

SELECT pg_temp.assert_min_rows((SELECT COUNT(*) FROM :"schema_name".pedidos), 500, 'pedidos');
SELECT pg_temp.assert_min_rows((SELECT COUNT(*) FROM :"schema_name".lineas_pedido), 1050, 'lineas_pedido');
SELECT pg_temp.assert_min_rows((SELECT COUNT(*) FROM :"schema_name".lecturas_sensores), 950, 'lecturas_sensores');
SELECT pg_temp.assert_min_rows((SELECT COUNT(*) FROM :"schema_name".consumos_material), 350, 'consumos_material');
SELECT pg_temp.assert_min_rows((SELECT COUNT(*) FROM :"schema_name".clientes), 1, 'clientes');
SELECT pg_temp.assert_min_rows((SELECT COUNT(*) FROM :"schema_name".productos), 1, 'productos');
SELECT pg_temp.assert_min_rows((SELECT COUNT(*) FROM :"schema_name".ordenes_produccion), 1, 'ordenes_produccion');

WITH target AS (
    SELECT id
    FROM :"schema_name".lecturas_sensores
    ORDER BY id
    LIMIT 350
),
deleted AS (
    DELETE FROM :"schema_name".lecturas_sensores lectura
    USING target
    WHERE lectura.id = target.id
    RETURNING 1
)
INSERT INTO cdc_demo_counts (step_order, operation, target_table, affected_rows)
SELECT 1, 'delete', 'lecturas_sensores', COUNT(*) FROM deleted;

WITH target AS (
    SELECT id
    FROM :"schema_name".pedidos
    ORDER BY fecha_pedido, id
    LIMIT 500
),
updated AS (
    UPDATE :"schema_name".pedidos pedido
    SET observaciones = pedido.observaciones || ' | CDC actualización: aislamiento, reparación y ensayo urgente.',
        importe_total = (pedido.importe_total * 1.01)::NUMERIC(12, 2)
    FROM target
    WHERE pedido.id = target.id
    RETURNING 1
)
INSERT INTO cdc_demo_counts (step_order, operation, target_table, affected_rows)
SELECT 2, 'update', 'pedidos', COUNT(*) FROM updated;

WITH base AS (
    SELECT COALESCE(MAX(id), 0) AS max_id
    FROM :"schema_name".productos
),
source_rows AS (
    SELECT base.max_id + serie.numero AS id,
           serie.numero AS numero
    FROM base
    CROSS JOIN generate_series(1, 10) AS serie(numero)
),
inserted AS (
    INSERT INTO :"schema_name".productos
        (id, codigo_producto, nombre, familia, modelo_transformador, precio_base, coste_unitario, activo, created_at)
    SELECT id,
           'CDC-PROD-' || id::TEXT,
           'Servicio CDC de reparación y ensayo ' || numero::TEXT,
           'servicios CDC alta tensión',
           'CDC-TR-9000',
           1850.00,
           940.00,
           1,
           TIMESTAMPTZ '2027-01-01 08:00:00+00' + (numero || ' minutes')::INTERVAL
    FROM source_rows
    RETURNING id
),
remembered AS (
    INSERT INTO cdc_demo_inserted_productos (id)
    SELECT id FROM inserted
    RETURNING 1
)
INSERT INTO cdc_demo_counts (step_order, operation, target_table, affected_rows)
SELECT 3, 'insert', 'productos', COUNT(*) FROM remembered;

WITH target AS (
    SELECT id
    FROM :"schema_name".lineas_pedido
    ORDER BY id
    LIMIT 350
),
deleted AS (
    DELETE FROM :"schema_name".lineas_pedido linea
    USING target
    WHERE linea.id = target.id
    RETURNING 1
)
INSERT INTO cdc_demo_counts (step_order, operation, target_table, affected_rows)
SELECT 4, 'delete', 'lineas_pedido', COUNT(*) FROM deleted;

WITH base AS (
    SELECT COALESCE(MAX(id), 0) AS max_id
    FROM :"schema_name".pedidos
),
clientes_disponibles AS (
    SELECT ARRAY_AGG(id ORDER BY id) AS ids,
           COUNT(*) AS total
    FROM :"schema_name".clientes
),
source_rows AS (
    SELECT base.max_id + serie.numero AS id,
           clientes_disponibles.ids[((serie.numero - 1) % clientes_disponibles.total) + 1] AS cliente_id,
           serie.numero AS numero
    FROM base
    CROSS JOIN clientes_disponibles
    CROSS JOIN generate_series(1, 120) AS serie(numero)
),
inserted AS (
    INSERT INTO :"schema_name".pedidos
        (id, cliente_id, numero_pedido, fecha_pedido, estado, observaciones, importe_total, created_at)
    SELECT id,
           cliente_id,
           'CDC-PED-' || id::TEXT,
           TIMESTAMPTZ '2027-01-01 10:00:00+00' + (numero || ' days')::INTERVAL,
           'confirmado',
           'Pedido CDC insertado con aislamiento, alta tensión y reparación planificada para nueva línea analítica.',
           0.00,
           TIMESTAMPTZ '2027-01-01 10:00:00+00' + (numero || ' days')::INTERVAL
    FROM source_rows
    RETURNING id
),
remembered AS (
    INSERT INTO cdc_demo_inserted_pedidos (id)
    SELECT id FROM inserted
    RETURNING 1
)
INSERT INTO cdc_demo_counts (step_order, operation, target_table, affected_rows)
SELECT 5, 'insert', 'pedidos', COUNT(*) FROM remembered;

WITH target AS (
    SELECT id
    FROM :"schema_name".lineas_pedido
    ORDER BY id
    LIMIT 700
),
updated AS (
    UPDATE :"schema_name".lineas_pedido linea
    SET precio_unitario = (linea.precio_unitario * 1.07)::NUMERIC(10, 2),
        descripcion = linea.descripcion || ' | CDC margen: aislamiento, cobre y alta tensión.'
    FROM target
    WHERE linea.id = target.id
    RETURNING linea.id
),
remembered AS (
    INSERT INTO cdc_demo_updated_lineas (id)
    SELECT id FROM updated
    RETURNING 1
)
INSERT INTO cdc_demo_counts (step_order, operation, target_table, affected_rows)
SELECT 6, 'update', 'lineas_pedido', COUNT(*) FROM remembered;

WITH base AS (
    SELECT COALESCE(MAX(id), 0) AS max_id
    FROM :"schema_name".lineas_pedido
),
pedidos_disponibles AS (
    SELECT ARRAY_AGG(id ORDER BY id) AS ids,
           COUNT(*) AS total
    FROM cdc_demo_inserted_pedidos
),
productos_disponibles AS (
    SELECT ARRAY_AGG(id ORDER BY id) AS ids,
           COUNT(*) AS total
    FROM cdc_demo_inserted_productos
),
source_rows AS (
    SELECT base.max_id + serie.numero AS id,
           pedidos_disponibles.ids[((serie.numero - 1) % pedidos_disponibles.total) + 1] AS pedido_id,
           productos_disponibles.ids[((serie.numero - 1) % productos_disponibles.total) + 1] AS producto_id,
           ((serie.numero - 1) % 2) + 1 AS numero_linea,
           serie.numero AS numero
    FROM base
    CROSS JOIN pedidos_disponibles
    CROSS JOIN productos_disponibles
    CROSS JOIN generate_series(1, 220) AS serie(numero)
),
inserted AS (
    INSERT INTO :"schema_name".lineas_pedido
        (id, pedido_id, producto_id, numero_linea, cantidad, precio_unitario, coste_unitario, descripcion, created_at)
    SELECT id,
           pedido_id,
           producto_id,
           numero_linea,
           3.00,
           1850.00,
           940.00,
           'Línea CDC insertada para servicios CDC alta tensión con aislamiento reforzado y ensayo final.',
           TIMESTAMPTZ '2027-01-01 12:00:00+00' + (numero || ' days')::INTERVAL
    FROM source_rows
    RETURNING 1
)
INSERT INTO cdc_demo_counts (step_order, operation, target_table, affected_rows)
SELECT 7, 'insert', 'lineas_pedido', COUNT(*) FROM inserted;

WITH target AS (
    SELECT id
    FROM cdc_demo_updated_lineas
    ORDER BY id
    LIMIT 200
),
updated AS (
    UPDATE :"schema_name".lineas_pedido linea
    SET precio_unitario = (linea.precio_unitario * 1.03)::NUMERIC(10, 2),
        descripcion = linea.descripcion || ' | CDC segunda actualización sobre la misma línea.'
    FROM target
    WHERE linea.id = target.id
    RETURNING 1
)
INSERT INTO cdc_demo_counts (step_order, operation, target_table, affected_rows)
SELECT 8, 'update', 'lineas_pedido', COUNT(*) FROM updated;

WITH target AS (
    SELECT id
    FROM :"schema_name".consumos_material
    ORDER BY id
    LIMIT 300
),
deleted AS (
    DELETE FROM :"schema_name".consumos_material consumo
    USING target
    WHERE consumo.id = target.id
    RETURNING 1
)
INSERT INTO cdc_demo_counts (step_order, operation, target_table, affected_rows)
SELECT 9, 'delete', 'consumos_material', COUNT(*) FROM deleted;

WITH base AS (
    SELECT COALESCE(MAX(id), 0) AS max_id
    FROM :"schema_name".lecturas_sensores
),
ordenes AS (
    SELECT id, maquina_id, ROW_NUMBER() OVER (ORDER BY id) AS rn
    FROM :"schema_name".ordenes_produccion
    ORDER BY id
    LIMIT 100
),
source_rows AS (
    SELECT base.max_id + ordenes.rn AS id,
           ordenes.id AS orden_produccion_id,
           ordenes.maquina_id,
           ordenes.rn AS numero
    FROM base
    JOIN ordenes ON TRUE
),
inserted AS (
    INSERT INTO :"schema_name".lecturas_sensores
        (id, orden_produccion_id, maquina_id, fecha_lectura, sensor_codigo, temperatura, vibracion, consumo_kw, fuera_rango, observaciones)
    SELECT id,
           orden_produccion_id,
           maquina_id,
           TIMESTAMPTZ '2027-05-01 13:00:00+00' + (numero || ' hours')::INTERVAL,
           'CDC-SENS-' || id::TEXT,
           165.00,
           12.50,
           410.00,
           1,
           'Lectura CDC insertada fuera de rango durante ensayo de alta tensión.'
    FROM source_rows
    RETURNING 1
)
INSERT INTO cdc_demo_counts (step_order, operation, target_table, affected_rows)
SELECT 10, 'insert', 'lecturas_sensores', COUNT(*) FROM inserted;

WITH target AS (
    SELECT id
    FROM :"schema_name".lecturas_sensores
    ORDER BY fecha_lectura DESC, id DESC
    LIMIT 600
),
updated AS (
    UPDATE :"schema_name".lecturas_sensores lectura
    SET temperatura = (lectura.temperatura + 4.25)::NUMERIC(10, 2),
        consumo_kw = (lectura.consumo_kw + 18.50)::NUMERIC(10, 2),
        fuera_rango = 1,
        observaciones = lectura.observaciones || ' | CDC actualización de sensor fuera de rango.'
    FROM target
    WHERE lectura.id = target.id
    RETURNING 1
)
INSERT INTO cdc_demo_counts (step_order, operation, target_table, affected_rows)
SELECT 11, 'update', 'lecturas_sensores', COUNT(*) FROM updated;

WITH base AS (
    SELECT COALESCE(MAX(id), 0) AS max_id
    FROM :"schema_name".no_conformidades
),
ordenes AS (
    SELECT id, ROW_NUMBER() OVER (ORDER BY id DESC) AS rn
    FROM :"schema_name".ordenes_produccion
    ORDER BY id DESC
    LIMIT 50
),
source_rows AS (
    SELECT base.max_id + ordenes.rn AS id,
           ordenes.id AS orden_produccion_id,
           ordenes.rn AS numero
    FROM base
    JOIN ordenes ON TRUE
),
inserted AS (
    INSERT INTO :"schema_name".no_conformidades
        (id, orden_produccion_id, codigo, fecha_deteccion, severidad, area, descripcion, coste_estimado, estado, observaciones)
    SELECT id,
           orden_produccion_id,
           'CDC-NC-' || id::TEXT,
           TIMESTAMPTZ '2027-06-01 14:00:00+00' + (numero || ' days')::INTERVAL,
           4,
           'ensayo eléctrico',
           'No conformidad CDC por aislamiento y aceite fuera de especificación.',
           8500.00,
           'abierta',
           'Requiere reparación, ensayo adicional y trazabilidad de material.'
    FROM source_rows
    RETURNING 1
)
INSERT INTO cdc_demo_counts (step_order, operation, target_table, affected_rows)
SELECT 12, 'insert', 'no_conformidades', COUNT(*) FROM inserted;

WITH totals AS (
    SELECT operation, SUM(affected_rows)::BIGINT AS affected_rows
    FROM cdc_demo_counts
    GROUP BY operation
),
expected AS (
    SELECT *
    FROM (
        VALUES ('delete', 1000::BIGINT),
               ('update', 2000::BIGINT),
               ('insert', 500::BIGINT)
    ) AS expected_rows(operation, affected_rows)
)
SELECT pg_temp.assert_exact_rows(totals.affected_rows, expected.affected_rows, expected.operation)
FROM expected
JOIN totals ON totals.operation = expected.operation;

SELECT operation, SUM(affected_rows)::BIGINT AS affected_rows
FROM cdc_demo_counts
GROUP BY operation
ORDER BY CASE operation
             WHEN 'delete' THEN 1
             WHEN 'update' THEN 2
             WHEN 'insert' THEN 3
             ELSE 4
         END;

COMMIT;

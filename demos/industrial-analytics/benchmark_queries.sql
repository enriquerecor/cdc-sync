\set ON_ERROR_STOP on

-- benchmark: 01_evolucion_mensual_facturacion
WITH base_facturacion AS (
    SELECT
        date_trunc('month', p.fecha_pedido) AS mes,
        pr.familia,
        c.id AS cliente_id,
        p.id AS pedido_id,
        lp.cantidad,
        lp.precio_unitario,
        lp.coste_unitario,
        lp.cantidad * lp.precio_unitario AS importe_linea,
        lp.cantidad * (lp.precio_unitario - lp.coste_unitario) AS margen_linea
    FROM :"schema_name".pedidos p
    JOIN :"schema_name".clientes c ON c.id = p.cliente_id
    JOIN :"schema_name".lineas_pedido lp ON lp.pedido_id = p.id
    JOIN :"schema_name".productos pr ON pr.id = lp.producto_id
),
facturacion_mensual AS (
    SELECT
        mes,
        familia,
        COUNT(DISTINCT cliente_id) AS clientes_distintos,
        COUNT(DISTINCT pedido_id) AS pedidos_distintos,
        SUM(importe_linea) AS facturacion,
        SUM(margen_linea) AS margen,
        MAX(precio_unitario) AS precio_maximo,
        AVG(importe_linea) AS ticket_medio_linea
    FROM base_facturacion
    GROUP BY mes, familia
)
SELECT
    mes,
    familia,
    clientes_distintos,
    pedidos_distintos,
    facturacion::NUMERIC(12, 2) AS facturacion,
    margen::NUMERIC(12, 2) AS margen,
    precio_maximo::NUMERIC(10, 2) AS precio_maximo,
    ticket_medio_linea::NUMERIC(10, 2) AS ticket_medio_linea,
    RANK() OVER (PARTITION BY mes ORDER BY facturacion DESC) AS ranking_mensual,
    (
        facturacion - LAG(facturacion) OVER (PARTITION BY familia ORDER BY mes)
    )::NUMERIC(12, 2) AS variacion_facturacion
FROM facturacion_mensual
ORDER BY mes, facturacion DESC;

-- benchmark: 02_busqueda_textual_historica
WITH texto_historico AS (
    SELECT
        EXTRACT(YEAR FROM p.fecha_pedido)::BIGINT AS anio,
        c.sector,
        pr.familia,
        c.id AS cliente_id,
        p.id AS pedido_id,
        lp.cantidad * lp.precio_unitario AS importe_linea,
        p.observaciones || ' ' || lp.descripcion || ' ' || pr.nombre AS texto_busqueda
    FROM :"schema_name".pedidos p
    JOIN :"schema_name".clientes c ON c.id = p.cliente_id
    JOIN :"schema_name".lineas_pedido lp ON lp.pedido_id = p.id
    JOIN :"schema_name".productos pr ON pr.id = lp.producto_id
),
coincidencias AS (
    SELECT
        anio,
        sector,
        familia,
        cliente_id,
        pedido_id,
        importe_linea,
        length(texto_busqueda) AS longitud_texto
    FROM texto_historico
    WHERE texto_busqueda ILIKE '%' || :'search_term' || '%'
)
SELECT
    anio,
    sector,
    familia,
    COUNT(DISTINCT pedido_id) AS pedidos_distintos,
    COUNT(DISTINCT cliente_id) AS clientes_distintos,
    SUM(importe_linea)::NUMERIC(12, 2) AS facturacion,
    AVG(longitud_texto)::NUMERIC(10, 2) AS longitud_media_texto,
    RANK() OVER (PARTITION BY anio, sector ORDER BY SUM(importe_linea) DESC) AS ranking_sector
FROM coincidencias
GROUP BY anio, sector, familia
ORDER BY anio, facturacion DESC;

-- benchmark: 03_sensores_por_hora_maquina_orden
WITH lecturas_enriquecidas AS (
    SELECT
        date_trunc('hour', ls.fecha_lectura) AS hora,
        m.codigo_maquina,
        m.area,
        pr.modelo_transformador,
        op.id AS orden_produccion_id,
        ls.temperatura,
        ls.vibracion,
        ls.consumo_kw,
        ls.fuera_rango,
        CASE
            WHEN ls.temperatura > 130 OR ls.vibracion > 10 OR ls.consumo_kw > 300 THEN 1
            ELSE 0
        END AS lectura_critica
    FROM :"schema_name".lecturas_sensores ls
    JOIN :"schema_name".maquinas m ON m.id = ls.maquina_id
    JOIN :"schema_name".ordenes_produccion op ON op.id = ls.orden_produccion_id
    JOIN :"schema_name".productos pr ON pr.id = op.producto_id
)
SELECT
    hora,
    codigo_maquina,
    area,
    modelo_transformador,
    COUNT(*) AS lecturas,
    COUNT(DISTINCT orden_produccion_id) AS ordenes_distintas,
    AVG(temperatura)::NUMERIC(10, 2) AS temperatura_media,
    percentile_cont(0.95) WITHIN GROUP (ORDER BY temperatura)::NUMERIC(10, 2) AS temperatura_p95,
    stddev_pop(vibracion)::NUMERIC(10, 2) AS vibracion_desviacion,
    MAX(consumo_kw)::NUMERIC(10, 2) AS consumo_kw_maximo,
    SUM(fuera_rango)::BIGINT AS lecturas_fuera_rango,
    SUM(lectura_critica)::BIGINT AS lecturas_criticas
FROM lecturas_enriquecidas
GROUP BY hora, codigo_maquina, area, modelo_transformador
ORDER BY hora DESC, lecturas_criticas DESC, consumo_kw_maximo DESC
LIMIT 500;

-- benchmark: 04_top_clientes_actividad_relevante
WITH actividad_cliente AS (
    SELECT
        c.id AS cliente_id,
        c.nombre,
        c.sector,
        p.id AS pedido_id,
        p.fecha_pedido,
        pr.familia,
        lp.cantidad,
        lp.precio_unitario,
        lp.cantidad * lp.precio_unitario AS importe_linea,
        lp.cantidad * (lp.precio_unitario - lp.coste_unitario) AS margen_linea
    FROM :"schema_name".clientes c
    JOIN :"schema_name".pedidos p ON p.cliente_id = c.id
    JOIN :"schema_name".lineas_pedido lp ON lp.pedido_id = p.id
    JOIN :"schema_name".productos pr ON pr.id = lp.producto_id
),
resumen_cliente AS (
    SELECT
        cliente_id,
        nombre,
        sector,
        COUNT(DISTINCT pedido_id) AS pedidos_distintos,
        COUNT(DISTINCT familia) AS familias_distintas,
        MAX(fecha_pedido) AS ultimo_pedido,
        SUM(importe_linea) AS facturacion,
        SUM(margen_linea) AS margen,
        AVG(precio_unitario) AS precio_medio_linea
    FROM actividad_cliente
    GROUP BY cliente_id, nombre, sector
    HAVING COUNT(DISTINCT pedido_id) >= 3
       AND SUM(importe_linea) > 10000
)
SELECT
    cliente_id,
    nombre,
    sector,
    pedidos_distintos,
    familias_distintas,
    ultimo_pedido,
    facturacion::NUMERIC(12, 2) AS facturacion,
    margen::NUMERIC(12, 2) AS margen,
    precio_medio_linea::NUMERIC(10, 2) AS precio_medio_linea,
    RANK() OVER (PARTITION BY sector ORDER BY facturacion DESC) AS ranking_sector
FROM resumen_cliente
ORDER BY facturacion DESC, ultimo_pedido DESC
LIMIT 50;

-- benchmark: 05_trazabilidad_calidad
WITH trazabilidad AS (
    SELECT
        date_trunc('month', nc.fecha_deteccion) AS mes,
        prov.nombre AS proveedor,
        prov.pais AS pais_proveedor,
        mat.familia AS familia_material,
        nc.id AS no_conformidad_id,
        nc.severidad,
        op.id AS orden_produccion_id,
        op.cantidad_real,
        cm.coste_consumido,
        lm.coste_total,
        nc.coste_estimado
    FROM :"schema_name".no_conformidades nc
    JOIN :"schema_name".ordenes_produccion op ON op.id = nc.orden_produccion_id
    JOIN :"schema_name".consumos_material cm ON cm.orden_produccion_id = op.id
    JOIN :"schema_name".lotes_material lm ON lm.id = cm.lote_material_id
    JOIN :"schema_name".materiales mat ON mat.id = lm.material_id
    JOIN :"schema_name".proveedores prov ON prov.id = lm.proveedor_id
)
SELECT
    mes,
    proveedor,
    pais_proveedor,
    familia_material,
    COUNT(DISTINCT no_conformidad_id) AS no_conformidades,
    COUNT(DISTINCT orden_produccion_id) AS ordenes_afectadas,
    AVG(severidad)::NUMERIC(10, 2) AS severidad_media,
    SUM(coste_estimado)::NUMERIC(12, 2) AS coste_calidad,
    SUM(coste_consumido)::NUMERIC(12, 2) AS coste_material_consumido,
    MAX(coste_total)::NUMERIC(12, 2) AS lote_mayor_coste,
    RANK() OVER (PARTITION BY mes ORDER BY SUM(coste_estimado) DESC) AS ranking_coste_mes
FROM trazabilidad
GROUP BY mes, proveedor, pais_proveedor, familia_material
ORDER BY mes, coste_calidad DESC;

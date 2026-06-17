\set ON_ERROR_STOP on

CREATE INDEX IF NOT EXISTS idx_clientes_sector
    ON :"schema_name".clientes (sector);

CREATE INDEX IF NOT EXISTS idx_productos_familia
    ON :"schema_name".productos (familia);

CREATE INDEX IF NOT EXISTS idx_pedidos_cliente_fecha
    ON :"schema_name".pedidos (cliente_id, fecha_pedido);

CREATE INDEX IF NOT EXISTS idx_lineas_pedido_pedido
    ON :"schema_name".lineas_pedido (pedido_id);

CREATE INDEX IF NOT EXISTS idx_lineas_pedido_producto
    ON :"schema_name".lineas_pedido (producto_id);

CREATE INDEX IF NOT EXISTS idx_ordenes_producto_maquina
    ON :"schema_name".ordenes_produccion (producto_id, maquina_id);

CREATE INDEX IF NOT EXISTS idx_lecturas_orden_fecha
    ON :"schema_name".lecturas_sensores (orden_produccion_id, fecha_lectura);

CREATE INDEX IF NOT EXISTS idx_lecturas_maquina_fecha
    ON :"schema_name".lecturas_sensores (maquina_id, fecha_lectura);

CREATE INDEX IF NOT EXISTS idx_lotes_material_material
    ON :"schema_name".lotes_material (material_id);

CREATE INDEX IF NOT EXISTS idx_lotes_material_proveedor
    ON :"schema_name".lotes_material (proveedor_id);

CREATE INDEX IF NOT EXISTS idx_consumos_orden
    ON :"schema_name".consumos_material (orden_produccion_id);

CREATE INDEX IF NOT EXISTS idx_consumos_lote
    ON :"schema_name".consumos_material (lote_material_id);

CREATE INDEX IF NOT EXISTS idx_no_conformidades_orden_fecha
    ON :"schema_name".no_conformidades (orden_produccion_id, fecha_deteccion);

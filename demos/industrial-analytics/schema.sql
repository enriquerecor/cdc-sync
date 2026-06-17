\set ON_ERROR_STOP on

DROP SCHEMA IF EXISTS :"schema_name" CASCADE;
CREATE SCHEMA :"schema_name";

CREATE TABLE :"schema_name".clientes
(
    id             BIGINT PRIMARY KEY,
    codigo_cliente TEXT           NOT NULL UNIQUE,
    nombre         TEXT           NOT NULL,
    sector         TEXT           NOT NULL,
    pais           TEXT           NOT NULL,
    activo         SMALLINT       NOT NULL,
    created_at     TIMESTAMPTZ(3) NOT NULL,
    CONSTRAINT clientes_id_positivo CHECK (id > 0),
    CONSTRAINT clientes_activo_uint8 CHECK (activo BETWEEN 0 AND 1)
);

CREATE TABLE :"schema_name".productos
(
    id                    BIGINT PRIMARY KEY,
    codigo_producto       TEXT           NOT NULL UNIQUE,
    nombre                TEXT           NOT NULL,
    familia               TEXT           NOT NULL,
    modelo_transformador  TEXT           NOT NULL,
    precio_base           NUMERIC(10, 2) NOT NULL,
    coste_unitario        NUMERIC(10, 2) NOT NULL,
    activo                SMALLINT       NOT NULL,
    created_at            TIMESTAMPTZ(3) NOT NULL,
    CONSTRAINT productos_id_positivo CHECK (id > 0),
    CONSTRAINT productos_activo_uint8 CHECK (activo BETWEEN 0 AND 1),
    CONSTRAINT productos_importes_positivos CHECK (precio_base >= 0 AND coste_unitario >= 0)
);

CREATE TABLE :"schema_name".pedidos
(
    id             BIGINT PRIMARY KEY,
    cliente_id     BIGINT         NOT NULL REFERENCES :"schema_name".clientes (id),
    numero_pedido  TEXT           NOT NULL UNIQUE,
    fecha_pedido   TIMESTAMPTZ(3) NOT NULL,
    estado         TEXT           NOT NULL,
    observaciones  TEXT           NOT NULL,
    importe_total  NUMERIC(12, 2) NOT NULL,
    created_at     TIMESTAMPTZ(3) NOT NULL,
    CONSTRAINT pedidos_id_positivo CHECK (id > 0),
    CONSTRAINT pedidos_importe_total_positivo CHECK (importe_total >= 0)
);

CREATE TABLE :"schema_name".lineas_pedido
(
    id             BIGINT PRIMARY KEY,
    pedido_id      BIGINT         NOT NULL REFERENCES :"schema_name".pedidos (id),
    producto_id    BIGINT         NOT NULL REFERENCES :"schema_name".productos (id),
    numero_linea   SMALLINT       NOT NULL,
    cantidad       NUMERIC(12, 2) NOT NULL,
    precio_unitario NUMERIC(10, 2) NOT NULL,
    coste_unitario NUMERIC(10, 2) NOT NULL,
    descripcion    TEXT           NOT NULL,
    created_at     TIMESTAMPTZ(3) NOT NULL,
    CONSTRAINT lineas_pedido_id_positivo CHECK (id > 0),
    CONSTRAINT lineas_pedido_numero_linea_uint8 CHECK (numero_linea BETWEEN 1 AND 255),
    CONSTRAINT lineas_pedido_cantidad_positiva CHECK (cantidad > 0),
    CONSTRAINT lineas_pedido_importes_positivos CHECK (precio_unitario >= 0 AND coste_unitario >= 0)
);

CREATE TABLE :"schema_name".maquinas
(
    id             BIGINT PRIMARY KEY,
    codigo_maquina TEXT           NOT NULL UNIQUE,
    area           TEXT           NOT NULL,
    tipo           TEXT           NOT NULL,
    estado         TEXT           NOT NULL,
    created_at     TIMESTAMPTZ(3) NOT NULL,
    CONSTRAINT maquinas_id_positivo CHECK (id > 0)
);

CREATE TABLE :"schema_name".ordenes_produccion
(
    id                    BIGINT PRIMARY KEY,
    producto_id           BIGINT         NOT NULL REFERENCES :"schema_name".productos (id),
    maquina_id            BIGINT         NOT NULL REFERENCES :"schema_name".maquinas (id),
    codigo_orden          TEXT           NOT NULL UNIQUE,
    fecha_inicio          TIMESTAMPTZ(3) NOT NULL,
    fecha_fin             TIMESTAMPTZ(3) NOT NULL,
    estado                TEXT           NOT NULL,
    cantidad_planificada  NUMERIC(12, 2) NOT NULL,
    cantidad_real         NUMERIC(12, 2) NOT NULL,
    observaciones         TEXT           NOT NULL,
    CONSTRAINT ordenes_produccion_id_positivo CHECK (id > 0),
    CONSTRAINT ordenes_produccion_cantidades_positivas CHECK (cantidad_planificada > 0 AND cantidad_real >= 0),
    CONSTRAINT ordenes_produccion_fechas_validas CHECK (fecha_fin >= fecha_inicio)
);

CREATE TABLE :"schema_name".lecturas_sensores
(
    id                  BIGINT PRIMARY KEY,
    orden_produccion_id BIGINT         NOT NULL REFERENCES :"schema_name".ordenes_produccion (id),
    maquina_id          BIGINT         NOT NULL REFERENCES :"schema_name".maquinas (id),
    fecha_lectura       TIMESTAMPTZ(3) NOT NULL,
    sensor_codigo       TEXT           NOT NULL,
    temperatura         NUMERIC(10, 2) NOT NULL,
    vibracion           NUMERIC(10, 2) NOT NULL,
    consumo_kw          NUMERIC(10, 2) NOT NULL,
    fuera_rango         SMALLINT       NOT NULL,
    observaciones       TEXT           NOT NULL,
    CONSTRAINT lecturas_sensores_id_positivo CHECK (id > 0),
    CONSTRAINT lecturas_sensores_fuera_rango_uint8 CHECK (fuera_rango BETWEEN 0 AND 1),
    CONSTRAINT lecturas_sensores_medidas_positivas CHECK (temperatura >= 0 AND vibracion >= 0 AND consumo_kw >= 0)
);

CREATE TABLE :"schema_name".proveedores
(
    id               BIGINT PRIMARY KEY,
    codigo_proveedor TEXT           NOT NULL UNIQUE,
    nombre           TEXT           NOT NULL,
    pais             TEXT           NOT NULL,
    sector           TEXT           NOT NULL,
    activo           SMALLINT       NOT NULL,
    created_at       TIMESTAMPTZ(3) NOT NULL,
    CONSTRAINT proveedores_id_positivo CHECK (id > 0),
    CONSTRAINT proveedores_activo_uint8 CHECK (activo BETWEEN 0 AND 1)
);

CREATE TABLE :"schema_name".materiales
(
    id              BIGINT PRIMARY KEY,
    codigo_material TEXT           NOT NULL UNIQUE,
    nombre          TEXT           NOT NULL,
    familia         TEXT           NOT NULL,
    coste_unitario  NUMERIC(10, 2) NOT NULL,
    activo          SMALLINT       NOT NULL,
    created_at      TIMESTAMPTZ(3) NOT NULL,
    CONSTRAINT materiales_id_positivo CHECK (id > 0),
    CONSTRAINT materiales_activo_uint8 CHECK (activo BETWEEN 0 AND 1),
    CONSTRAINT materiales_coste_unitario_positivo CHECK (coste_unitario >= 0)
);

CREATE TABLE :"schema_name".lotes_material
(
    id                BIGINT PRIMARY KEY,
    material_id       BIGINT         NOT NULL REFERENCES :"schema_name".materiales (id),
    proveedor_id      BIGINT         NOT NULL REFERENCES :"schema_name".proveedores (id),
    codigo_lote       TEXT           NOT NULL UNIQUE,
    fecha_recepcion   TIMESTAMPTZ(3) NOT NULL,
    cantidad_recibida NUMERIC(12, 2) NOT NULL,
    coste_total       NUMERIC(12, 2) NOT NULL,
    estado            TEXT           NOT NULL,
    observaciones     TEXT           NOT NULL,
    CONSTRAINT lotes_material_id_positivo CHECK (id > 0),
    CONSTRAINT lotes_material_cantidad_positiva CHECK (cantidad_recibida > 0),
    CONSTRAINT lotes_material_coste_total_positivo CHECK (coste_total >= 0)
);

CREATE TABLE :"schema_name".consumos_material
(
    id                  BIGINT PRIMARY KEY,
    orden_produccion_id BIGINT         NOT NULL REFERENCES :"schema_name".ordenes_produccion (id),
    lote_material_id    BIGINT         NOT NULL REFERENCES :"schema_name".lotes_material (id),
    fecha_consumo       TIMESTAMPTZ(3) NOT NULL,
    cantidad_consumida  NUMERIC(12, 2) NOT NULL,
    coste_consumido     NUMERIC(12, 2) NOT NULL,
    CONSTRAINT consumos_material_id_positivo CHECK (id > 0),
    CONSTRAINT consumos_material_cantidad_positiva CHECK (cantidad_consumida > 0),
    CONSTRAINT consumos_material_coste_positivo CHECK (coste_consumido >= 0)
);

CREATE TABLE :"schema_name".no_conformidades
(
    id                  BIGINT PRIMARY KEY,
    orden_produccion_id BIGINT         NOT NULL REFERENCES :"schema_name".ordenes_produccion (id),
    codigo              TEXT           NOT NULL UNIQUE,
    fecha_deteccion     TIMESTAMPTZ(3) NOT NULL,
    severidad           SMALLINT       NOT NULL,
    area                TEXT           NOT NULL,
    descripcion         TEXT           NOT NULL,
    coste_estimado      NUMERIC(12, 2) NOT NULL,
    estado              TEXT           NOT NULL,
    observaciones       TEXT           NOT NULL,
    CONSTRAINT no_conformidades_id_positivo CHECK (id > 0),
    CONSTRAINT no_conformidades_severidad_uint8 CHECK (severidad BETWEEN 1 AND 5),
    CONSTRAINT no_conformidades_coste_positivo CHECK (coste_estimado >= 0)
);

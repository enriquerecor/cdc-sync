#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import os
import random
import re
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Iterable, Sequence

ROOT_DIR = Path(__file__).resolve().parents[2]
DEMO_DIR = Path(__file__).resolve().parent
SCHEMA_SQL = DEMO_DIR / "schema.sql"
INDEXES_SQL = DEMO_DIR / "indexes.sql"
BENCHMARK_QUERIES_SQL = DEMO_DIR / "benchmark_queries.sql"
CDC_CHANGES_SQL = DEMO_DIR / "cdc_changes.sql"
DEFAULT_SCHEMA = "industrial_analytics"
DEFAULT_SEED = 20260617
DEFAULT_SEARCH_TERM = "aislamiento"
DATE_START = datetime(2020, 1, 1, tzinfo=timezone.utc)
DATE_END = datetime(2026, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
TWO_DECIMALS = Decimal("0.01")
IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class AnalyticsDatasetError(RuntimeError):
    pass


@dataclass(frozen=True)
class VolumePreset:
    clientes: int
    productos: int
    proveedores: int
    materiales: int
    lotes_material: int
    maquinas: int
    pedidos: int
    lineas_por_pedido: int
    ordenes_produccion: int
    lecturas_por_orden: int
    consumos_por_orden: int
    no_conformidades: int


@dataclass(frozen=True)
class DatasetConfig:
    size: str
    seed: int
    volume: VolumePreset


@dataclass(frozen=True)
class ClienteDTO:
    id: int
    sector: str


@dataclass(frozen=True)
class ProductoDTO:
    id: int
    familia: str
    modelo_transformador: str
    precio_base: Decimal
    coste_unitario: Decimal


@dataclass(frozen=True)
class ProveedorDTO:
    id: int
    pais: str


@dataclass(frozen=True)
class MaterialDTO:
    id: int
    familia: str
    coste_unitario: Decimal


@dataclass(frozen=True)
class LoteMaterialDTO:
    id: int
    material_id: int
    proveedor_id: int
    familia_material: str
    coste_unitario: Decimal


@dataclass(frozen=True)
class MaquinaDTO:
    id: int
    area: str


@dataclass(frozen=True)
class PedidoDTO:
    id: int
    cliente_id: int
    fecha_pedido: datetime
    estado: str
    observaciones: str
    created_at: datetime


@dataclass(frozen=True)
class OrdenProduccionDTO:
    id: int
    producto_id: int
    maquina_id: int
    fecha_inicio: datetime
    fecha_fin: datetime
    area: str


@dataclass(frozen=True)
class TableFile:
    name: str
    columns: tuple[str, ...]
    path: Path
    row_count: int


@dataclass(frozen=True)
class BenchmarkQuery:
    name: str
    sql: str


@dataclass(frozen=True)
class PsqlConfig:
    service: str
    database: str
    user: str


PRESETS: dict[str, VolumePreset] = {
    "small": VolumePreset(
        clientes=80,
        productos=80,
        proveedores=24,
        materiales=80,
        lotes_material=160,
        maquinas=10,
        pedidos=1_000,
        lineas_por_pedido=3,
        ordenes_produccion=300,
        lecturas_por_orden=12,
        consumos_por_orden=3,
        no_conformidades=45,
    ),
    "medium": VolumePreset(
        clientes=4_000,
        productos=1_500,
        proveedores=400,
        materiales=2_000,
        lotes_material=5_000,
        maquinas=80,
        pedidos=250_000,
        lineas_por_pedido=3,
        ordenes_produccion=60_000,
        lecturas_por_orden=24,
        consumos_por_orden=3,
        no_conformidades=4_800,
    ),
    "large": VolumePreset(
        clientes=12_000,
        productos=3_500,
        proveedores=900,
        materiales=5_000,
        lotes_material=15_000,
        maquinas=160,
        pedidos=1_000_000,
        lineas_por_pedido=4,
        ordenes_produccion=180_000,
        lecturas_por_orden=24,
        consumos_por_orden=4,
        no_conformidades=16_000,
    ),
}

TABLE_COLUMNS: dict[str, tuple[str, ...]] = {
    "clientes": (
        "id",
        "codigo_cliente",
        "nombre",
        "sector",
        "pais",
        "activo",
        "created_at",
    ),
    "productos": (
        "id",
        "codigo_producto",
        "nombre",
        "familia",
        "modelo_transformador",
        "precio_base",
        "coste_unitario",
        "activo",
        "created_at",
    ),
    "pedidos": (
        "id",
        "cliente_id",
        "numero_pedido",
        "fecha_pedido",
        "estado",
        "observaciones",
        "importe_total",
        "created_at",
    ),
    "lineas_pedido": (
        "id",
        "pedido_id",
        "producto_id",
        "numero_linea",
        "cantidad",
        "precio_unitario",
        "coste_unitario",
        "descripcion",
        "created_at",
    ),
    "maquinas": (
        "id",
        "codigo_maquina",
        "area",
        "tipo",
        "estado",
        "created_at",
    ),
    "ordenes_produccion": (
        "id",
        "producto_id",
        "maquina_id",
        "codigo_orden",
        "fecha_inicio",
        "fecha_fin",
        "estado",
        "cantidad_planificada",
        "cantidad_real",
        "observaciones",
    ),
    "lecturas_sensores": (
        "id",
        "orden_produccion_id",
        "maquina_id",
        "fecha_lectura",
        "sensor_codigo",
        "temperatura",
        "vibracion",
        "consumo_kw",
        "fuera_rango",
        "observaciones",
    ),
    "proveedores": (
        "id",
        "codigo_proveedor",
        "nombre",
        "pais",
        "sector",
        "activo",
        "created_at",
    ),
    "materiales": (
        "id",
        "codigo_material",
        "nombre",
        "familia",
        "coste_unitario",
        "activo",
        "created_at",
    ),
    "lotes_material": (
        "id",
        "material_id",
        "proveedor_id",
        "codigo_lote",
        "fecha_recepcion",
        "cantidad_recibida",
        "coste_total",
        "estado",
        "observaciones",
    ),
    "consumos_material": (
        "id",
        "orden_produccion_id",
        "lote_material_id",
        "fecha_consumo",
        "cantidad_consumida",
        "coste_consumido",
    ),
    "no_conformidades": (
        "id",
        "orden_produccion_id",
        "codigo",
        "fecha_deteccion",
        "severidad",
        "area",
        "descripcion",
        "coste_estimado",
        "estado",
        "observaciones",
    ),
}

LOAD_ORDER = (
    "proveedores",
    "materiales",
    "clientes",
    "productos",
    "maquinas",
    "lotes_material",
    "pedidos",
    "lineas_pedido",
    "ordenes_produccion",
    "lecturas_sensores",
    "consumos_material",
    "no_conformidades",
)

CLIENT_SECTORS = (
    "energía",
    "renovables",
    "siderurgia",
    "naval",
    "ferroviario",
    "distribución eléctrica",
    "química",
    "minería",
)
COUNTRIES = ("España", "Portugal", "Francia", "Italia", "Marruecos", "Alemania")
COMPANY_PREFIXES = (
    "Iber",
    "Norte",
    "Atlas",
    "Delta",
    "Ebro",
    "Cantabria",
    "Tajo",
    "Levante",
)
COMPANY_SUFFIXES = (
    "Transformación",
    "Energía",
    "Subestaciones",
    "Metalurgia",
    "Infraestructuras",
    "Industrial",
)
PRODUCT_FAMILIES = (
    "transformadores de potencia",
    "transformadores secos",
    "bobinas especiales",
    "sistemas de aislamiento",
    "celdas de alta tensión",
    "kits de reparación",
)
PRODUCT_NAMES = (
    "transformador encapsulado",
    "bobina de cobre",
    "núcleo magnético",
    "kit de aislamiento",
    "celda de alta tensión",
    "módulo de ensayo",
)
MATERIAL_FAMILIES = (
    "cobre",
    "aceite dieléctrico",
    "núcleo magnético",
    "aislamiento sólido",
    "acero eléctrico",
    "resina epoxi",
)
MACHINE_AREAS = (
    "bobinado",
    "montaje",
    "ensayo eléctrico",
    "impregnación",
    "corte de núcleo",
    "reparación",
)
INDUSTRIAL_TERMS = (
    "aislamiento",
    "transformador",
    "bobina",
    "aceite",
    "cobre",
    "núcleo",
    "alta tensión",
    "ensayo",
    "reparación",
)
ORDER_STATES = ("borrador", "confirmado", "fabricado", "facturado")
PRODUCTION_STATES = ("planificada", "en curso", "terminada", "cerrada")
LOT_STATES = ("liberado", "bloqueado", "consumido")
QUALITY_STATES = ("abierta", "en análisis", "cerrada")


class PsqlClient:
    def __init__(self, config: PsqlConfig) -> None:
        self.config = config

    def run_sql_file(self, path: Path, variables: dict[str, str]) -> str:
        _require_file(path)
        return self.run_sql(path.read_text(encoding="utf-8"), variables)

    def run_sql(self, sql: str, variables: dict[str, str] | None = None) -> str:
        command = self._base_command(variables or {})
        result = subprocess.run(
            command,
            cwd=ROOT_DIR,
            input=sql,
            capture_output=True,
            text=True,
            check=False,
        )
        return _completed_output(command, result)

    def query(self, sql: str, variables: dict[str, str]) -> str:
        command = self._base_command(variables) + ["-qAt"]
        result = subprocess.run(
            command,
            cwd=ROOT_DIR,
            input=sql,
            capture_output=True,
            text=True,
            check=False,
        )
        return _completed_output(command, result)

    def report_sql_file(self, path: Path, variables: dict[str, str]) -> str:
        _require_file(path)
        command = self._base_command(variables) + ["-qAt"]
        result = subprocess.run(
            command,
            cwd=ROOT_DIR,
            input=path.read_text(encoding="utf-8"),
            capture_output=True,
            text=True,
            check=False,
        )
        return _completed_output(command, result)

    def copy_csv(self, schema_name: str, table_file: TableFile) -> str:
        schema_identifier = quote_identifier(schema_name)
        table_identifier = quote_identifier(table_file.name)
        column_list = ", ".join(quote_identifier(column) for column in table_file.columns)
        sql = (
            f"COPY {schema_identifier}.{table_identifier} ({column_list}) "
            "FROM STDIN WITH (FORMAT csv, HEADER true);"
        )
        command = self._base_command({}) + ["-c", sql]
        with table_file.path.open("rb") as csv_file:
            result = subprocess.run(
                command,
                cwd=ROOT_DIR,
                stdin=csv_file,
                capture_output=True,
                text=False,
                check=False,
            )

        return _completed_binary_output(command, result)

    def _base_command(self, variables: dict[str, str]) -> list[str]:
        command = [
            "docker",
            "compose",
            "exec",
            "-T",
            self.config.service,
            "psql",
            "-v",
            "ON_ERROR_STOP=1",
            "-U",
            self.config.user,
            "-d",
            self.config.database,
        ]
        for key, value in variables.items():
            command.extend(["-v", f"{key}={value}"])
        return command


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        command_handlers = {
            "load": run_load_command,
            "changes": run_changes_command,
            "benchmark": run_benchmark_command,
        }
        command_handlers[args.command](args)
        return 0
    except AnalyticsDatasetError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


def run_load_command(args: argparse.Namespace) -> None:
    schema_name = validate_identifier(args.schema)
    config = resolve_dataset_config(args)
    psql_client = PsqlClient(resolve_psql_config(args))
    print(
        "Generando dataset "
        f"{config.size} con seed={config.seed} en esquema {schema_name}"
    )

    csv_dir_context = csv_directory_context(args.csv_dir)
    with csv_dir_context as csv_dir_raw:
        csv_dir = Path(csv_dir_raw)
        table_files = generate_dataset(config, csv_dir)
        psql_client.run_sql_file(SCHEMA_SQL, {"schema_name": schema_name})
        print(f"Esquema recreado: {schema_name}")
        for table_name in LOAD_ORDER:
            table_file = table_files[table_name]
            psql_client.copy_csv(schema_name, table_file)
            print(f"COPY {table_name}: {table_file.row_count} filas")
        psql_client.run_sql_file(INDEXES_SQL, {"schema_name": schema_name})
        print("Índices creados")


def run_benchmark_command(args: argparse.Namespace) -> None:
    schema_name = validate_identifier(args.schema)
    psql_client = PsqlClient(resolve_psql_config(args))
    queries = load_benchmark_queries(BENCHMARK_QUERIES_SQL)
    variables = {
        "schema_name": schema_name,
        "search_term": args.term,
    }
    print(f"Ejecutando benchmark en PostgreSQL sobre {schema_name}")
    for query in queries:
        started_at = time.perf_counter()
        output = psql_client.query(query.sql, variables)
        elapsed_ms = (time.perf_counter() - started_at) * 1000
        row_count = count_output_rows(output)
        result_signature = hashlib.sha256(output.encode("utf-8")).hexdigest()[:12]
        print(
            f"{query.name}: {elapsed_ms:.1f} ms "
            f"({row_count} filas, firma {result_signature})"
        )


def run_changes_command(args: argparse.Namespace) -> None:
    schema_name = validate_identifier(args.schema)
    psql_client = PsqlClient(resolve_psql_config(args))
    output = psql_client.report_sql_file(CDC_CHANGES_SQL, {"schema_name": schema_name})
    print(f"Cambios CDC aplicados sobre {schema_name}")
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if line:
            print(f"  {line}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Genera y carga un dataset ERP industrial sintético.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    load_parser = subparsers.add_parser(
        "load",
        help="Genera y carga datos en PostgreSQL.",
    )
    add_postgres_arguments(load_parser)
    load_parser.add_argument("--size", choices=sorted(PRESETS), default="small")
    load_parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    load_parser.add_argument("--scale", type=positive_float, default=1.0)
    load_parser.add_argument("--csv-dir", type=Path)
    load_parser.add_argument("--clientes", type=positive_int)
    load_parser.add_argument("--productos", type=positive_int)
    load_parser.add_argument("--proveedores", type=positive_int)
    load_parser.add_argument("--materiales", type=positive_int)
    load_parser.add_argument("--lotes-material", type=positive_int)
    load_parser.add_argument("--maquinas", type=positive_int)
    load_parser.add_argument("--pedidos", type=positive_int)
    load_parser.add_argument("--lineas-por-pedido", type=positive_int)
    load_parser.add_argument("--ordenes-produccion", type=positive_int)
    load_parser.add_argument("--lecturas-por-orden", type=positive_int)
    load_parser.add_argument("--consumos-por-orden", type=positive_int)
    load_parser.add_argument("--no-conformidades", type=positive_int)

    changes_parser = subparsers.add_parser(
        "changes",
        help="Aplica cambios transaccionales para una futura demo CDC.",
    )
    add_postgres_arguments(changes_parser)

    benchmark_parser = subparsers.add_parser(
        "benchmark",
        help="Ejecuta las queries benchmark y muestra tiempos aproximados.",
    )
    add_postgres_arguments(benchmark_parser)
    benchmark_parser.add_argument("--term", default=DEFAULT_SEARCH_TERM)
    return parser


def add_postgres_arguments(parser: argparse.ArgumentParser) -> None:
    env = load_environment()
    parser.add_argument("--schema", default=DEFAULT_SCHEMA)
    parser.add_argument("--postgres-service", default="postgres")
    parser.add_argument("--database", default=env.get("POSTGRES_DB", "cdc_sync"))
    parser.add_argument("--user", default=env.get("POSTGRES_USER", "cdc_sync"))


def resolve_dataset_config(args: argparse.Namespace) -> DatasetConfig:
    preset = scale_preset(PRESETS[args.size], args.scale)
    volume = VolumePreset(
        clientes=override_int(preset.clientes, args.clientes),
        productos=override_int(preset.productos, args.productos),
        proveedores=override_int(preset.proveedores, args.proveedores),
        materiales=override_int(preset.materiales, args.materiales),
        lotes_material=override_int(preset.lotes_material, args.lotes_material),
        maquinas=override_int(preset.maquinas, args.maquinas),
        pedidos=override_int(preset.pedidos, args.pedidos),
        lineas_por_pedido=override_int(
            preset.lineas_por_pedido,
            args.lineas_por_pedido,
        ),
        ordenes_produccion=override_int(
            preset.ordenes_produccion,
            args.ordenes_produccion,
        ),
        lecturas_por_orden=override_int(
            preset.lecturas_por_orden,
            args.lecturas_por_orden,
        ),
        consumos_por_orden=override_int(
            preset.consumos_por_orden,
            args.consumos_por_orden,
        ),
        no_conformidades=override_int(
            preset.no_conformidades,
            args.no_conformidades,
        ),
    )
    return DatasetConfig(size=args.size, seed=args.seed, volume=volume)


def resolve_psql_config(args: argparse.Namespace) -> PsqlConfig:
    return PsqlConfig(
        service=args.postgres_service,
        database=args.database,
        user=args.user,
    )


def scale_preset(preset: VolumePreset, scale: float) -> VolumePreset:
    if scale == 1.0:
        return preset

    return replace(
        preset,
        clientes=scale_count(preset.clientes, scale),
        productos=scale_count(preset.productos, scale),
        proveedores=scale_count(preset.proveedores, scale),
        materiales=scale_count(preset.materiales, scale),
        lotes_material=scale_count(preset.lotes_material, scale),
        maquinas=scale_count(preset.maquinas, scale),
        pedidos=scale_count(preset.pedidos, scale),
        ordenes_produccion=scale_count(preset.ordenes_produccion, scale),
        no_conformidades=scale_count(preset.no_conformidades, scale),
    )


def generate_dataset(config: DatasetConfig, output_dir: Path) -> dict[str, TableFile]:
    rng = random.Random(config.seed)
    output_dir.mkdir(parents=True, exist_ok=True)
    generated: dict[str, TableFile] = {}

    proveedores, generated["proveedores"] = write_proveedores(rng, output_dir, config)
    materiales, generated["materiales"] = write_materiales(rng, output_dir, config)
    clientes, generated["clientes"] = write_clientes(rng, output_dir, config)
    productos, generated["productos"] = write_productos(rng, output_dir, config)
    maquinas, generated["maquinas"] = write_maquinas(rng, output_dir, config)
    lotes, generated["lotes_material"] = write_lotes_material(
        rng,
        output_dir,
        config,
        materiales,
        proveedores,
    )
    pedidos, pedido_totals = build_pedidos(rng, config, clientes)
    generated["lineas_pedido"] = write_lineas_pedido(
        rng,
        output_dir,
        config,
        pedidos,
        productos,
        pedido_totals,
    )
    generated["pedidos"] = write_pedidos(output_dir, pedidos, pedido_totals)
    ordenes, generated["ordenes_produccion"] = write_ordenes_produccion(
        rng,
        output_dir,
        config,
        productos,
        maquinas,
    )
    generated["lecturas_sensores"] = write_lecturas_sensores(
        rng,
        output_dir,
        config,
        ordenes,
    )
    generated["consumos_material"] = write_consumos_material(
        rng,
        output_dir,
        config,
        ordenes,
        lotes,
    )
    generated["no_conformidades"] = write_no_conformidades(
        rng,
        output_dir,
        config,
        ordenes,
    )
    return generated


def write_proveedores(
    rng: random.Random,
    output_dir: Path,
    config: DatasetConfig,
) -> tuple[list[ProveedorDTO], TableFile]:
    proveedores: list[ProveedorDTO] = []

    def rows() -> Iterable[Sequence[object]]:
        for proveedor_id in range(1, config.volume.proveedores + 1):
            pais = rng.choice(COUNTRIES)
            proveedores.append(ProveedorDTO(id=proveedor_id, pais=pais))
            yield (
                proveedor_id,
                code("PROV", proveedor_id),
                company_name(rng, proveedor_id),
                pais,
                rng.choice(MATERIAL_FAMILIES),
                active_flag(rng),
                timestamp_text(random_datetime(rng)),
            )

    return proveedores, write_table(output_dir, "proveedores", rows())


def write_materiales(
    rng: random.Random,
    output_dir: Path,
    config: DatasetConfig,
) -> tuple[list[MaterialDTO], TableFile]:
    materiales: list[MaterialDTO] = []

    def rows() -> Iterable[Sequence[object]]:
        for material_id in range(1, config.volume.materiales + 1):
            familia = rng.choice(MATERIAL_FAMILIES)
            coste_unitario = money(rng, 2, 900)
            materiales.append(
                MaterialDTO(
                    id=material_id,
                    familia=familia,
                    coste_unitario=coste_unitario,
                )
            )
            yield (
                material_id,
                code("MAT", material_id),
                f"{familia} industrial {material_id:05d}",
                familia,
                decimal_text(coste_unitario),
                active_flag(rng),
                timestamp_text(random_datetime(rng)),
            )

    return materiales, write_table(output_dir, "materiales", rows())


def write_clientes(
    rng: random.Random,
    output_dir: Path,
    config: DatasetConfig,
) -> tuple[list[ClienteDTO], TableFile]:
    clientes: list[ClienteDTO] = []

    def rows() -> Iterable[Sequence[object]]:
        for cliente_id in range(1, config.volume.clientes + 1):
            sector = rng.choice(CLIENT_SECTORS)
            clientes.append(ClienteDTO(id=cliente_id, sector=sector))
            yield (
                cliente_id,
                code("CLI", cliente_id),
                company_name(rng, cliente_id),
                sector,
                rng.choice(COUNTRIES),
                active_flag(rng),
                timestamp_text(random_datetime(rng)),
            )

    return clientes, write_table(output_dir, "clientes", rows())


def write_productos(
    rng: random.Random,
    output_dir: Path,
    config: DatasetConfig,
) -> tuple[list[ProductoDTO], TableFile]:
    productos: list[ProductoDTO] = []

    def rows() -> Iterable[Sequence[object]]:
        for producto_id in range(1, config.volume.productos + 1):
            familia = rng.choice(PRODUCT_FAMILIES)
            modelo_transformador = f"TR-{rng.choice(('A', 'B', 'C', 'D'))}-{rng.randint(25, 800)}"
            coste_unitario = money(rng, 120, 45_000)
            precio_base = decimal_text_value(
                coste_unitario * Decimal(rng.randint(125, 220)) / Decimal(100)
            )
            productos.append(
                ProductoDTO(
                    id=producto_id,
                    familia=familia,
                    modelo_transformador=modelo_transformador,
                    precio_base=precio_base,
                    coste_unitario=coste_unitario,
                )
            )
            yield (
                producto_id,
                code("PROD", producto_id),
                f"{rng.choice(PRODUCT_NAMES)} {modelo_transformador}",
                familia,
                modelo_transformador,
                decimal_text(precio_base),
                decimal_text(coste_unitario),
                active_flag(rng),
                timestamp_text(random_datetime(rng)),
            )

    return productos, write_table(output_dir, "productos", rows())


def write_maquinas(
    rng: random.Random,
    output_dir: Path,
    config: DatasetConfig,
) -> tuple[list[MaquinaDTO], TableFile]:
    maquinas: list[MaquinaDTO] = []

    def rows() -> Iterable[Sequence[object]]:
        for maquina_id in range(1, config.volume.maquinas + 1):
            area = MACHINE_AREAS[(maquina_id - 1) % len(MACHINE_AREAS)]
            maquinas.append(MaquinaDTO(id=maquina_id, area=area))
            yield (
                maquina_id,
                code("MAQ", maquina_id),
                area,
                rng.choice(("bobinadora", "horno", "banco de ensayo", "corte CNC")),
                rng.choice(("operativa", "mantenimiento", "ajuste")),
                timestamp_text(random_datetime(rng)),
            )

    return maquinas, write_table(output_dir, "maquinas", rows())


def write_lotes_material(
    rng: random.Random,
    output_dir: Path,
    config: DatasetConfig,
    materiales: Sequence[MaterialDTO],
    proveedores: Sequence[ProveedorDTO],
) -> tuple[list[LoteMaterialDTO], TableFile]:
    lotes: list[LoteMaterialDTO] = []

    def rows() -> Iterable[Sequence[object]]:
        for lote_id in range(1, config.volume.lotes_material + 1):
            material = rng.choice(materiales)
            proveedor = rng.choice(proveedores)
            cantidad = quantity(rng, 100, 20_000)
            coste_total = decimal_text_value(cantidad * material.coste_unitario)
            lotes.append(
                LoteMaterialDTO(
                    id=lote_id,
                    material_id=material.id,
                    proveedor_id=proveedor.id,
                    familia_material=material.familia,
                    coste_unitario=material.coste_unitario,
                )
            )
            yield (
                lote_id,
                material.id,
                proveedor.id,
                code("LOTE", lote_id),
                timestamp_text(random_datetime(rng)),
                decimal_text(cantidad),
                decimal_text(coste_total),
                rng.choice(LOT_STATES),
                industrial_text(rng, lote_id, "Recepción de lote"),
            )

    return lotes, write_table(output_dir, "lotes_material", rows())


def build_pedidos(
    rng: random.Random,
    config: DatasetConfig,
    clientes: Sequence[ClienteDTO],
) -> tuple[list[PedidoDTO], dict[int, Decimal]]:
    pedidos: list[PedidoDTO] = []
    pedido_totals: dict[int, Decimal] = {}
    for pedido_id in range(1, config.volume.pedidos + 1):
        fecha_pedido = random_datetime(rng)
        pedidos.append(
            PedidoDTO(
                id=pedido_id,
                cliente_id=rng.choice(clientes).id,
                fecha_pedido=fecha_pedido,
                estado=rng.choice(ORDER_STATES),
                observaciones=industrial_text(rng, pedido_id, "Pedido industrial"),
                created_at=fecha_pedido,
            )
        )
        pedido_totals[pedido_id] = Decimal("0.00")

    return pedidos, pedido_totals


def write_lineas_pedido(
    rng: random.Random,
    output_dir: Path,
    config: DatasetConfig,
    pedidos: Sequence[PedidoDTO],
    productos: Sequence[ProductoDTO],
    pedido_totals: dict[int, Decimal],
) -> TableFile:
    def rows() -> Iterable[Sequence[object]]:
        linea_id = 1
        for pedido in pedidos:
            line_count = varied_count(rng, config.volume.lineas_por_pedido)
            for numero_linea in range(1, line_count + 1):
                producto = rng.choice(productos)
                cantidad = quantity(rng, 1, 12)
                precio_unitario = varied_decimal(rng, producto.precio_base, 90, 118)
                coste_unitario = varied_decimal(rng, producto.coste_unitario, 96, 104)
                pedido_totals[pedido.id] += decimal_text_value(cantidad * precio_unitario)
                yield (
                    linea_id,
                    pedido.id,
                    producto.id,
                    numero_linea,
                    decimal_text(cantidad),
                    decimal_text(precio_unitario),
                    decimal_text(coste_unitario),
                    industrial_text(rng, linea_id, producto.familia),
                    timestamp_text(pedido.created_at),
                )
                linea_id += 1

    return write_table(output_dir, "lineas_pedido", rows())


def write_pedidos(
    output_dir: Path,
    pedidos: Sequence[PedidoDTO],
    pedido_totals: dict[int, Decimal],
) -> TableFile:
    def rows() -> Iterable[Sequence[object]]:
        for pedido in pedidos:
            yield (
                pedido.id,
                pedido.cliente_id,
                code("PED", pedido.id),
                timestamp_text(pedido.fecha_pedido),
                pedido.estado,
                pedido.observaciones,
                decimal_text(pedido_totals[pedido.id]),
                timestamp_text(pedido.created_at),
            )

    return write_table(output_dir, "pedidos", rows())


def write_ordenes_produccion(
    rng: random.Random,
    output_dir: Path,
    config: DatasetConfig,
    productos: Sequence[ProductoDTO],
    maquinas: Sequence[MaquinaDTO],
) -> tuple[list[OrdenProduccionDTO], TableFile]:
    ordenes: list[OrdenProduccionDTO] = []

    def rows() -> Iterable[Sequence[object]]:
        for orden_id in range(1, config.volume.ordenes_produccion + 1):
            producto = rng.choice(productos)
            maquina = rng.choice(maquinas)
            fecha_inicio = random_datetime(rng, DATE_END - timedelta(days=10))
            fecha_fin = min(fecha_inicio + timedelta(hours=rng.randint(4, 96)), DATE_END)
            cantidad_planificada = quantity(rng, 1, 80)
            cantidad_real = varied_decimal(rng, cantidad_planificada, 88, 107)
            ordenes.append(
                OrdenProduccionDTO(
                    id=orden_id,
                    producto_id=producto.id,
                    maquina_id=maquina.id,
                    fecha_inicio=fecha_inicio,
                    fecha_fin=fecha_fin,
                    area=maquina.area,
                )
            )
            yield (
                orden_id,
                producto.id,
                maquina.id,
                code("OP", orden_id),
                timestamp_text(fecha_inicio),
                timestamp_text(fecha_fin),
                rng.choice(PRODUCTION_STATES),
                decimal_text(cantidad_planificada),
                decimal_text(cantidad_real),
                industrial_text(rng, orden_id, producto.modelo_transformador),
            )

    return ordenes, write_table(output_dir, "ordenes_produccion", rows())


def write_lecturas_sensores(
    rng: random.Random,
    output_dir: Path,
    config: DatasetConfig,
    ordenes: Sequence[OrdenProduccionDTO],
) -> TableFile:
    def rows() -> Iterable[Sequence[object]]:
        lectura_id = 1
        for orden in ordenes:
            for lectura_offset in range(config.volume.lecturas_por_orden):
                fuera_rango = out_of_range_flag(rng)
                temperatura = sensor_value(rng, 45, 120, fuera_rango, 140, 180)
                vibracion = sensor_value(rng, 1, 8, fuera_rango, 9, 18)
                consumo_kw = sensor_value(rng, 20, 280, fuera_rango, 300, 520)
                fecha_lectura = min(
                    orden.fecha_inicio + timedelta(hours=lectura_offset),
                    DATE_END,
                )
                yield (
                    lectura_id,
                    orden.id,
                    orden.maquina_id,
                    timestamp_text(fecha_lectura),
                    f"SENS-{orden.maquina_id:03d}-{lectura_offset % 8:02d}",
                    decimal_text(temperatura),
                    decimal_text(vibracion),
                    decimal_text(consumo_kw),
                    fuera_rango,
                    industrial_text(rng, lectura_id, orden.area),
                )
                lectura_id += 1

    return write_table(output_dir, "lecturas_sensores", rows())


def write_consumos_material(
    rng: random.Random,
    output_dir: Path,
    config: DatasetConfig,
    ordenes: Sequence[OrdenProduccionDTO],
    lotes: Sequence[LoteMaterialDTO],
) -> TableFile:
    def rows() -> Iterable[Sequence[object]]:
        consumo_id = 1
        for orden in ordenes:
            for consumo_offset in range(config.volume.consumos_por_orden):
                lote = rng.choice(lotes)
                cantidad = quantity(rng, 1, 250)
                coste_consumido = decimal_text_value(cantidad * lote.coste_unitario)
                fecha_consumo = min(
                    orden.fecha_inicio + timedelta(hours=consumo_offset * 2),
                    DATE_END,
                )
                yield (
                    consumo_id,
                    orden.id,
                    lote.id,
                    timestamp_text(fecha_consumo),
                    decimal_text(cantidad),
                    decimal_text(coste_consumido),
                )
                consumo_id += 1

    return write_table(output_dir, "consumos_material", rows())


def write_no_conformidades(
    rng: random.Random,
    output_dir: Path,
    config: DatasetConfig,
    ordenes: Sequence[OrdenProduccionDTO],
) -> TableFile:
    def rows() -> Iterable[Sequence[object]]:
        for no_conformidad_id in range(1, config.volume.no_conformidades + 1):
            orden = rng.choice(ordenes)
            fecha_deteccion = min(orden.fecha_fin + timedelta(hours=rng.randint(1, 72)), DATE_END)
            yield (
                no_conformidad_id,
                orden.id,
                code("NC", no_conformidad_id),
                timestamp_text(fecha_deteccion),
                rng.randint(1, 5),
                orden.area,
                industrial_text(rng, no_conformidad_id, "No conformidad"),
                decimal_text(money(rng, 150, 25_000)),
                rng.choice(QUALITY_STATES),
                industrial_text(rng, no_conformidad_id + 17, "Acción correctiva"),
            )

    return write_table(output_dir, "no_conformidades", rows())


def write_table(
    output_dir: Path,
    table_name: str,
    rows: Iterable[Sequence[object]],
) -> TableFile:
    columns = TABLE_COLUMNS[table_name]
    path = output_dir / f"{table_name}.csv"
    row_count = 0
    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(columns)
        for row in rows:
            writer.writerow(row)
            row_count += 1

    return TableFile(name=table_name, columns=columns, path=path, row_count=row_count)


def load_benchmark_queries(path: Path) -> list[BenchmarkQuery]:
    _require_file(path)
    queries: list[BenchmarkQuery] = []
    current_name = ""
    current_lines: list[str] = []

    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("-- benchmark:"):
            append_benchmark_query(queries, current_name, current_lines)
            current_name = line.removeprefix("-- benchmark:").strip()
            current_lines = []
            continue

        if current_name:
            current_lines.append(line)

    append_benchmark_query(queries, current_name, current_lines)
    if queries:
        return queries

    raise AnalyticsDatasetError(f"No hay queries benchmark en {path}")


def append_benchmark_query(
    queries: list[BenchmarkQuery],
    name: str,
    lines: Sequence[str],
) -> None:
    if not name:
        return

    sql = "\n".join(lines).strip()
    if not sql:
        raise AnalyticsDatasetError(f"La query benchmark {name} está vacía")

    queries.append(BenchmarkQuery(name=name, sql=sql))


def csv_directory_context(csv_dir: Path | None) -> tempfile.TemporaryDirectory | CsvDirContext:
    if csv_dir is None:
        return tempfile.TemporaryDirectory(prefix="industrial-analytics-")

    return CsvDirContext(csv_dir)


class CsvDirContext:
    def __init__(self, path: Path) -> None:
        self.path = path

    def __enter__(self) -> Path:
        self.path.mkdir(parents=True, exist_ok=True)
        return self.path

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> bool:
        return False


def load_environment() -> dict[str, str]:
    env = {
        "POSTGRES_DB": "cdc_sync",
        "POSTGRES_USER": "cdc_sync",
    }
    env.update(read_dotenv(ROOT_DIR / ".env"))
    env.update({key: value for key, value in os.environ.items() if value is not None})
    return env


def read_dotenv(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, raw_value = line.split("=", 1)
        values[key.strip()] = raw_value.strip().strip('"').strip("'")

    return values


def count_output_rows(output: str) -> int:
    return sum(1 for line in output.splitlines() if line.strip())


def override_int(default: int, override: int | None) -> int:
    if override is None:
        return default

    return override


def positive_int(raw_value: str) -> int:
    value = int(raw_value)
    if value > 0:
        return value

    raise argparse.ArgumentTypeError("Debe ser un entero positivo")


def positive_float(raw_value: str) -> float:
    value = float(raw_value)
    if value > 0:
        return value

    raise argparse.ArgumentTypeError("Debe ser un número positivo")


def scale_count(value: int, scale: float) -> int:
    return max(1, round(value * scale))


def validate_identifier(value: str) -> str:
    if IDENTIFIER_PATTERN.fullmatch(value):
        return value

    raise AnalyticsDatasetError(f"Identificador SQL no válido: {value}")


def quote_identifier(identifier: str) -> str:
    validate_identifier(identifier)
    return f'"{identifier}"'


def _require_file(path: Path) -> None:
    if path.exists():
        return

    raise AnalyticsDatasetError(f"No existe el fichero requerido: {path}")


def _completed_output(
    command: Sequence[str],
    result: subprocess.CompletedProcess[str],
) -> str:
    if result.returncode == 0:
        return result.stdout

    raise AnalyticsDatasetError(command_error(command, result.stdout, result.stderr))


def _completed_binary_output(
    command: Sequence[str],
    result: subprocess.CompletedProcess[bytes],
) -> str:
    stdout = result.stdout.decode("utf-8", errors="replace")
    stderr = result.stderr.decode("utf-8", errors="replace")
    if result.returncode == 0:
        return stdout

    raise AnalyticsDatasetError(command_error(command, stdout, stderr))


def command_error(command: Sequence[str], stdout: str, stderr: str) -> str:
    command_text = " ".join(command)
    output = stderr.strip() or stdout.strip()
    if output:
        return f"Falló el comando: {command_text}\n{output}"

    return f"Falló el comando: {command_text}"


def code(prefix: str, value: int) -> str:
    return f"{prefix}-{value:08d}"


def company_name(rng: random.Random, value: int) -> str:
    return (
        f"{rng.choice(COMPANY_PREFIXES)} {rng.choice(COMPANY_SUFFIXES)} "
        f"{value:05d}"
    )


def active_flag(rng: random.Random) -> int:
    if rng.random() < 0.95:
        return 1

    return 0


def out_of_range_flag(rng: random.Random) -> int:
    if rng.random() < 0.08:
        return 1

    return 0


def varied_count(rng: random.Random, base_value: int) -> int:
    delta = rng.choice((-1, 0, 0, 1))
    return max(1, base_value + delta)


def money(rng: random.Random, minimum: int, maximum: int) -> Decimal:
    cents = rng.randint(minimum * 100, maximum * 100)
    return decimal_text_value(Decimal(cents) / Decimal(100))


def quantity(rng: random.Random, minimum: int, maximum: int) -> Decimal:
    cents = rng.randint(minimum * 100, maximum * 100)
    return decimal_text_value(Decimal(cents) / Decimal(100))


def varied_decimal(
    rng: random.Random,
    value: Decimal,
    minimum_percent: int,
    maximum_percent: int,
) -> Decimal:
    factor = Decimal(rng.randint(minimum_percent, maximum_percent)) / Decimal(100)
    return decimal_text_value(value * factor)


def sensor_value(
    rng: random.Random,
    normal_minimum: int,
    normal_maximum: int,
    fuera_rango: int,
    alert_minimum: int,
    alert_maximum: int,
) -> Decimal:
    if fuera_rango == 1:
        return money(rng, alert_minimum, alert_maximum)

    return money(rng, normal_minimum, normal_maximum)


def decimal_text_value(value: Decimal) -> Decimal:
    return value.quantize(TWO_DECIMALS, rounding=ROUND_HALF_UP)


def decimal_text(value: Decimal) -> str:
    return f"{decimal_text_value(value):.2f}"


def random_datetime(
    rng: random.Random,
    latest_start: datetime | None = None,
) -> datetime:
    latest = latest_start or DATE_END
    span_milliseconds = int((latest - DATE_START).total_seconds() * 1000)
    offset = rng.randrange(span_milliseconds)
    return DATE_START + timedelta(milliseconds=offset)


def timestamp_text(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="milliseconds")


def industrial_text(rng: random.Random, value: int, context: str) -> str:
    term = industrial_term(rng, value)
    templates = (
        "{context}: revisión de {term} con trazabilidad completa.",
        "{context}: ajuste de {term} tras ensayo de calidad.",
        "{context}: seguimiento de {term} en fabricación industrial.",
        "{context}: observación sobre {term} y reparación preventiva.",
    )
    return rng.choice(templates).format(context=context, term=term)


def industrial_term(rng: random.Random, value: int) -> str:
    if value % 5 == 0:
        return "aislamiento"

    return rng.choice(INDUSTRIAL_TERMS)


if __name__ == "__main__":
    raise SystemExit(main())

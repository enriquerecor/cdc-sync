# PostgreSQL

## Alcance en esta fase

- base `cdc_sync`
- tablas de prueba `customers` y `orders`
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
```

Comprobar soporte CDC:

```bash
docker compose exec postgres psql -U cdc_sync -d cdc_sync -c "SHOW wal_level;"
```

Resultado esperado:

- existen `customers` y `orders`
- `wal_level` devuelve `logical`

## Reset del servicio

Los scripts de inicialización solo se ejecutan cuando el volumen está vacío.

```bash
docker compose down -v
docker compose up -d postgres
```

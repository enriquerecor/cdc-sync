# cdc-sync

Sistema configurable de sincronización CDC entre una base de datos transaccional y una base de datos analítica.

```text
PostgreSQL (OLTP) -> Debezium -> Kafka -> Worker (Python) -> ClickHouse
                      ^
                      |
FastAPI (control plane) -> PostgreSQL (control plane)
                      ^
                      |
Frontend administrativo (React)
```

El repositorio contiene una solución acotada, completa y preparada para evolucionar: API del control plane, consola
administrativa, infraestructura CDC, workers stateless y destino analítico ClickHouse. La configuración funcional se
persiste en PostgreSQL desde la API y la interfaz; cada worker arranca con `WORKER_ID`, solicita su contrato runtime y
mantiene esa configuración en memoria hasta un reinicio manual.

## Requisitos previos

- Docker y Docker Compose.
- `make`.
- `python3`, usado por los scripts del recorrido local.
- `npm`, solo si se ejecutan comandos del frontend fuera de Docker.

## Inicio rápido

Desde una instalación limpia, preparar el entorno y ejecutar la validación completa:

```bash
make env-init
make e2e-validate
```

Abrir la consola administrativa:

```bash
make frontend-up
```

```text
http://localhost:5173
```

Resultado esperado:

- la validación termina con `PostgreSQL y ClickHouse están reconciliados`;
- la API responde en `http://localhost:8000`;
- la consola carga con el indicador de API operativo.

## Documentación técnica

- [Stack local](docs/local-stack.md)
- [API REST](docs/api.md)
- [Modelo del control plane](docs/control-plane-model.md)
- [Frontend administrativo](frontend/README.md)
- [Worker](docs/worker.md)
- [PostgreSQL](docs/postgresql.md)
- [Kafka y ZooKeeper](docs/kafka.md)
- [Debezium](docs/debezium.md)
- [ClickHouse](docs/clickhouse.md)

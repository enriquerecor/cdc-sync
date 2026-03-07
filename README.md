# cdc-sync

Sistema configurable de sincronización entre BBDD transaccionales y BBDD analíticas que, mediante CDC, permite replicar
tablas seleccionadas con distintas políticas de actualización (_batch_, casi en tiempo real o bajo demanda),
garantizando consistencia y resiliencia ante fallos.

## Entorno local

La infraestructura local se construirá por fases para validar cada pieza antes de añadir la siguiente.
Este documento irá creciendo con nuevas secciones a medida que se incorporen más servicios al `docker-compose`.

### Preparación general

Copiar el fichero de ejemplo si se quiere personalizar usuario, contraseña, base de datos o puerto:

```bash
cp .env.example .env
```

Por ahora solo se usan variables para PostgreSQL. Se añadirán nuevas secciones al mismo fichero cuando entren Kafka,
Debezium, ClickHouse y el worker.

## 1. PostgreSQL

Primer paso de infraestructura local: PostgreSQL con dos tablas de prueba (`customers` y `orders`) creadas
automáticamente al arrancar Docker.

### 1.1 Levantar PostgreSQL

```bash
docker compose up -d postgres
```

Con la configuración por defecto de `.env.example`, la base de datos queda disponible en `localhost:5432` con estas
credenciales:

- Base de datos: `cdc_sync`
- Usuario: `cdc_sync`
- Contraseña: `cdc_sync`

### 1.2 Validar el estado del servicio

Comprobar que los contenedores están sanos:

```bash
docker compose ps
```

Listar las tablas creadas:

```bash
docker compose exec postgres psql -U cdc_sync -d cdc_sync -c "\\dt"
```

### 1.3 Validar datos de ejemplo

Consultar los datos de ejemplo:

```bash
docker compose exec postgres psql -U cdc_sync -d cdc_sync -c "SELECT * FROM customers;"
docker compose exec postgres psql -U cdc_sync -d cdc_sync -c "SELECT * FROM orders;"
```

### 1.4 Reiniciar el entorno desde cero

Los scripts de inicialización de PostgreSQL solo se ejecutan cuando el volumen de datos está vacío. Para reconstruir la
base desde cero:

```bash
docker compose down -v
docker compose up -d postgres
```

## 2. ZooKeeper y Kafka

Segundo paso de infraestructura local: añadir la capa de mensajería base para que el stack pueda incorporar después
Debezium y el worker.

Aunque Kafka moderno puede desplegarse sin ZooKeeper, por ser menos común, se decide ceñirse al stack con ZooKeeper.

### 2.1 Levantar ZooKeeper y Kafka

```bash
docker compose up -d zookeeper kafka
```

Con la configuración por defecto de `.env.example`:

- ZooKeeper queda disponible en `localhost:2181`
- Kafka queda disponible en `localhost:9092` para clientes del host
- Kafka expone `kafka:29092` para el resto de contenedores del `docker-compose`

### 2.2 Validar el estado de los servicios

Comprobar que ambos contenedores están sanos:

```bash
docker compose ps
```

Validar que el broker responde dentro de la red Docker:

```bash
docker compose exec kafka cub kafka-ready 1 30 -b kafka:29092
```

### 2.3 Reiniciar ZooKeeper y Kafka desde cero

Si fuera necesario recrear solo esta parte del stack:

```bash
docker compose stop kafka zookeeper
docker compose rm -f kafka zookeeper
docker compose up -d zookeeper kafka
```

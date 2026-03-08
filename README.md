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

Actualmente el fichero incluye variables para PostgreSQL, ZooKeeper, Kafka y Debezium Connect. Se añadirán nuevas
secciones cuando entren ClickHouse y el worker.

La configuracion de conectores Debezium se versiona como plantilla sin secretos. Las credenciales reales deben quedar
solo en `.env` en local o en el sistema de despliegue del entorno correspondiente.

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

### 2.4 Validar publicación y consumo en Kafka

Crear el topic técnico de prueba:

```bash
docker compose exec kafka kafka-topics --create \
  --if-not-exists \
  --topic cdc-sync-test \
  --bootstrap-server kafka:29092 \
  --partitions 1 \
  --replication-factor 1
```

Publicar un mensaje de ejemplo:

```bash
printf 'ping-kafka-ejemplo\n' | docker compose exec -T kafka kafka-console-producer \
  --topic cdc-sync-test \
  --bootstrap-server kafka:29092
```

Consumir un mensaje y salir tras recibirlo:

```bash
docker compose exec kafka kafka-console-consumer \
  --topic cdc-sync-test \
  --bootstrap-server kafka:29092 \
  --from-beginning \
  --max-messages 1
```

El resultado esperado es que el consumidor muestre `ping-kafka-ejemplo` por pantalla y finalice.

## 3. Debezium Connect

Tercer paso de infraestructura local: añadir el servicio base de Kafka Connect con la imagen oficial de Debezium,
dejando la captura CDC para el siguiente corte.

### 3.1 Levantar Debezium Connect

```bash
docker compose up -d connect
```

Con la configuración por defecto de `.env.example`, la API REST de Connect queda disponible en `localhost:8083`.

### 3.2 Validar el estado del servicio

Comprobar que el contenedor está sano:

```bash
docker compose ps
```

Comprobar que la API REST responde:

```bash
curl -fsS http://localhost:8083/
```

Comprobar que los plugins de conectores están disponibles:

```bash
curl -fsS http://localhost:8083/connector-plugins
```

### 3.3 Reiniciar Debezium Connect desde cero

Si fuera necesario recrear solo este servicio:

```bash
docker compose stop connect
docker compose rm -f connect
docker compose up -d connect
```

### 3.4 Flujo comun para conectores Debezium

Antes de registrar el conector, PostgreSQL debe estar recreado con `wal_level=logical`:

```bash
docker compose up -d --force-recreate postgres
docker compose exec postgres psql -U cdc_sync -d cdc_sync -c "SHOW wal_level;"
```

El resultado esperado es `logical`.

Las plantillas versionadas y las convenciones comunes estan en:

```bash
infrastructure/debezium/connectors/README.md
```

Renderizar la plantilla del conector con variables locales:

```bash
./infrastructure/debezium/connectors/render-template.sh \
  infrastructure/debezium/connectors/postgresql/source.config.template.json \
  infrastructure/debezium/connectors/generated/postgresql-source.local.json
```

Aplicar la configuracion renderizada de forma idempotente:

```bash
curl -fsS -X PUT http://localhost:8083/connectors/postgres-cdc-source/config \
  -H "Content-Type: application/json" \
  --data @infrastructure/debezium/connectors/generated/postgresql-source.local.json
```

La configuracion renderizada queda fuera de Git para evitar subir credenciales locales.

### 3.5 Registrar el conector PostgreSQL de ejemplo

La plantilla especifica de PostgreSQL esta en:

```bash
infrastructure/debezium/connectors/postgresql/source.config.template.json
```

La estructura ya reserva carpetas independientes para futuros conectores de `mysql` y `mariadb`.

Comprobar el estado del conector PostgreSQL:

```bash
curl -fsS http://localhost:8083/connectors/postgres-cdc-source/status
```

El resultado esperado es que el conector y su única tarea queden en estado `RUNNING`.

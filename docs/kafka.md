# Kafka y ZooKeeper

## Alcance en esta fase

- ZooKeeper como coordinación del broker local
- Kafka como capa de mensajería para eventos CDC
- persistencia explícita en volúmenes con nombre

## Arranque

```bash
docker compose up -d zookeeper kafka
```

Puertos por defecto:

- ZooKeeper: `localhost:2181`
- Kafka externo: `localhost:9092`
- Kafka interno entre contenedores: `kafka:29092`

## Validaciones

Comprobar estado:

```bash
docker compose ps
```

Validar disponibilidad del broker:

```bash
docker compose exec kafka cub kafka-ready 1 30 -b kafka:29092
```

## Topic técnico de prueba

Crear topic:

```bash
docker compose exec kafka kafka-topics --create \
  --if-not-exists \
  --topic cdc-sync-test \
  --bootstrap-server kafka:29092 \
  --partitions 1 \
  --replication-factor 1
```

Publicar mensaje:

```bash
printf 'ping-kafka-ejemplo\n' | docker compose exec -T kafka kafka-console-producer \
  --topic cdc-sync-test \
  --bootstrap-server kafka:29092
```

Consumir mensaje:

```bash
docker compose exec kafka kafka-console-consumer \
  --topic cdc-sync-test \
  --bootstrap-server kafka:29092 \
  --from-beginning \
  --max-messages 1
```

Resultado esperado:

- el consumidor imprime `ping-kafka-ejemplo`

## Recreación y reset

Recrear solo contenedores:

```bash
docker compose stop kafka zookeeper
docker compose rm -f kafka zookeeper
docker compose up -d zookeeper kafka
```

Limpiar también el estado persistido:

```bash
docker compose down -v
docker compose up -d
```

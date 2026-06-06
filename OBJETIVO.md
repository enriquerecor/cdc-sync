## Objetivo del MVP

El objetivo de este MVP es construir una base profesional para un sistema configurable de sincronización CDC entre una
base de datos transaccional y una base de datos analítica.

El sistema debe permitir desplegar varios workers desde este repositorio. Cada worker se identificará mediante una
variable de entorno `WORKER_ID`. Al arrancar, el worker hará una petición automática a la API REST del control plane,
enviará su identificador y recibirá la configuración runtime que debe ejecutar. Esa configuración se validará al inicio,
se mantendrá en memoria durante toda la vida del proceso y no cambiará hasta que el worker se reinicie manualmente.

La configuración se gestionará desde una interfaz de usuario. Desde esa interfaz se podrán crear y modificar workers,
conexiones a bases de datos de origen, destinos analíticos y configuraciones de tablas asignadas a cada worker. Toda la
información administrativa vivirá en PostgreSQL, que será la fuente de verdad del control plane.

La ejecución mínima del MVP será:

1. El usuario crea o modifica una configuración desde la interfaz.
2. La API persiste la configuración en PostgreSQL.
3. La API materializa la parte necesaria del origen en Kafka Connect mediante Debezium.
4. El usuario arranca o reinicia manualmente un worker con su `WORKER_ID`.
5. El worker solicita `GET /workers/{id}/config`.
6. La API devuelve un contrato runtime estable y validado.
7. El worker consume eventos CDC de Kafka y persiste los cambios en ClickHouse con versionado.

## Alcance funcional

El MVP debe cubrir de forma real, aunque acotada:

- gestión de varios workers;
- gestión de conexiones de origen PostgreSQL;
- gestión de destinos ClickHouse;
- asignación de tablas y claves primarias por configuración;
- materialización mínima e idempotente de conectores Debezium en Kafka Connect;
- contrato runtime por worker;
- worker stateless que arranca con `WORKER_ID` y carga configuración remota;
- persistencia versionada en ClickHouse;
- interfaz de usuario mínima para crear y editar configuraciones;
- validaciones estrictas y errores explícitos ante configuraciones incompatibles.

## Alcance técnico

Tecnologías del MVP:

- **Frontend:** React + TypeScript.
- **API REST / control plane:** FastAPI + Python.
- **Persistencia del control plane:** PostgreSQL.
- **Origen CDC inicial:** PostgreSQL.
- **Captura de cambios:** Debezium.
- **Transporte de eventos:** Apache Kafka.
- **Worker:** Python.
- **Destino analítico inicial:** ClickHouse.
- **Migraciones:** Alembic.
- **Orquestación local:** Docker Compose y `make`.

La arquitectura debe mantener separadas las responsabilidades:

- la UI administra configuración, pero no ejecuta sincronizaciones;
- la API decide, valida, persiste y materializa configuración;
- Kafka Connect captura cambios del origen;
- el worker procesa eventos y escribe en destino;
- ClickHouse queda aislado como primer adapter OLAP, no como dependencia del núcleo de decisión.

## Orden sano de implementación

El orden recomendado para las issues actuales es:

1. **#24 Modelo persistente del control plane para workers y configuraciones.**
   Definir la base real en PostgreSQL: workers, conexiones de origen, destinos, configuraciones y asignación publicada.

2. **#25 Gestión administrativa de workers y configuraciones del control plane.**
   Exponer la API administrativa mínima que consumirá la interfaz.

3. **#27 Gestionar Kafka Connect desde el control plane.**
   Implementar una materialización mínima, explícita e idempotente de conectores Debezium a partir de la configuración.

4. **#26 Contrato runtime por worker y endpoint `GET /workers/{id}/config`.**
   Compilar la configuración administrativa a un contrato runtime estable para el data plane.

5. **#28 Worker stateless con `WORKER_ID` y carga remota de configuración.**
   Sustituir la configuración local del worker por la carga inicial desde la API.

6. **#29 OpenAPI y tests básicos del control plane por worker.**
   Cerrar el contrato público y proteger los flujos críticos con tests.

Las issues posteriores de observabilidad, consultas temporales, cambios de esquema o coordinación avanzada deben quedar
fuera de esta primera vertical, salvo que sean imprescindibles para desbloquear el flujo anterior.

## Restricciones para completarlo 

Para que el MVP sea programable el alcance debe ser estricto:

- soportar solo PostgreSQL como origen inicial;
- soportar solo ClickHouse como destino inicial;
- soportar solo sincronización `realtime`;
- no implementar recarga en caliente de workers;
- no implementar polling periódico de configuración;
- no implementar reconciliación continua de Kafka Connect;
- no implementar retries avanzados, DLQ ni recuperación distribuida;
- no implementar autenticación ni gestión de usuarios si bloquea el flujo principal;
- no implementar cifrado completo de secretos en esta fase;
- no implementar soporte multi-tenant;
- no implementar batch, sincronización bajo demanda ni scheduling;
- no implementar soporte para cambios de esquema;
- mantener la interfaz de usuario como una herramienta administrativa mínima y funcional.

La gestión de credenciales en PostgreSQL es aceptable para el MVP, pero debe documentarse como decisión acotada. La API
no debe exponer secretos en respuestas de lectura salvo que sea estrictamente necesario para un flujo concreto. El modelo
debe quedar preparado para sustituir esa gestión por cifrado o un gestor de secretos en una fase profesional posterior.

## Criterio de éxito

El MVP se considera logrado cuando se pueda demostrar el siguiente flujo completo:

1. Crear desde la interfaz una configuración para un worker.
2. Persistir origen, destino y tablas en PostgreSQL mediante la API.
3. Materializar el conector Debezium correspondiente en Kafka Connect.
4. Arrancar manualmente el worker con `WORKER_ID`.
5. Obtener automáticamente la configuración runtime desde la API.
6. Insertar, modificar o borrar datos en PostgreSQL.
7. Ver los cambios reflejados en ClickHouse mediante el modelo versionado.
8. Modificar la configuración en la interfaz y comprobar que el cambio solo afecta tras reiniciar el worker.

Este MVP no debe ser un prototipo desechable. Debe ser una vertical pequeña, pero con fronteras limpias, contratos
explícitos y adapters sustituibles para que pueda evolucionar hacia un producto profesional.

## Caso de uso

Este documento se concreta con más detalle operativo en [OBJETIVO.md](OBJETIVO.md).

Una empresa dispone de un ERP u otra aplicación que opera sobre una BBDD transaccional (OLTP), pero necesita explotar
analítica pesada y búsquedas masivas en una BBDD analítica (OLAP) sin degradar el rendimiento del sistema principal.
El sistema permite crear, desde una interfaz gráfica, varios workers y sus configuraciones: credenciales de conexión a
la base de datos de origen, credenciales de conexión al destino analítico y tablas de las que se encargará cada worker.

La configuración queda almacenada en PostgreSQL como fuente de verdad del control plane. Cuando un worker arranca, se
identifica mediante un `WORKER_ID` definido en una variable de entorno, solicita automáticamente su configuración a la
API REST, la mantiene en memoria durante toda la ejecución y empieza a consumir eventos CDC. Los cambios posteriores de
configuración realizados desde la interfaz no afectan a un worker ya arrancado hasta que se reinicie manualmente.

La herramienta gestiona la traducción de los cambios a un modelo analítico consistente, basado en versionado y borrado
lógico, evitando la corrupción de la BBDD analítica dentro del alcance del MVP.

## Tecnologías a implementar

* **Frontend:** React + TypeScript, interfaz de configuración de workers, conexiones, destinos y tablas.
* **Backend / API REST:** Python + FastAPI, control plane para gestionar workers, conexiones de origen, destinos,
  configuraciones y contrato runtime por worker.
* **Persistencia del control plane:** PostgreSQL, con migraciones mediante Alembic.
* **BBDD transaccional de origen inicial:** PostgreSQL.
* **Captura de cambios (CDC):** Debezium para detectar _inserts_, _updates_ y _deletes_.
* **_Streaming_ de eventos:** Apache Kafka como canal de transporte de cambios.
* **Gestión de conectores CDC:** Kafka Connect, materializado desde la API a partir de la configuración persistida.
* **_Worker_ de procesamiento:** Python, encargado de consumir eventos, aplicar lógica de versionado y persistir los
  cambios en destino.
* **BBDD analítica de destino inicial:** ClickHouse, con modelo basado en versionado e indicadores de borrado lógico para
  garantizar consistencia.
* **Orquestación local:** Docker Compose y `make`.

> Nota: el diseño de microservicios debe permitir que, a mayores del desarrollo que formará parte del trabajo, en el
> futuro sea posible:
> * Sustituir la parte del _worker_ específica para ClickHouse por otra para otra OLAP (p. e.: BigQuery).
> * Sustituir el frontend por otro o por una CLI, pudiendo consumir la misma API REST.
> * Sustituir PostgreSQL como origen inicial por otros motores soportados por Debezium.
> * Sustituir la gestión simple de credenciales por cifrado o un gestor de secretos.

## Alcance del MVP

El MVP se limita a una vertical completa y reutilizable:

* Crear y editar workers desde la interfaz.
* Crear y editar conexiones de origen PostgreSQL.
* Crear y editar destinos ClickHouse.
* Crear configuraciones que asignen tablas a workers.
* Persistir toda la configuración administrativa en PostgreSQL.
* Materializar de forma mínima e idempotente el conector Debezium necesario en Kafka Connect.
* Exponer un endpoint runtime `GET /workers/{id}/config`.
* Arrancar workers stateless con `WORKER_ID`.
* Mantener la configuración fija en memoria hasta reinicio manual del worker.
* Persistir en ClickHouse eventos versionados de `INSERT`, `UPDATE` y `DELETE` lógico.

Quedan fuera del MVP inicial:

* recarga en caliente de workers;
* polling periódico de configuración;
* reconciliación continua de Kafka Connect;
* sincronización batch o bajo demanda;
* soporte multi-origen o multi-destino más allá de PostgreSQL y ClickHouse;
* autenticación, autorización y gestión de usuarios;
* cifrado completo de secretos;
* retries avanzados, DLQ y coordinación distribuida;
* soporte automático de cambios de esquema.

## Propuesta de valor

> A FUTURO: diseñar solución para que, cuando se añade una columna en una tabla de la BD OLTP, se pueda sincronizar
> con la BD OLAP sin tener que re-sincronizar la tabla completa.

### Configuración orientada a negocio

* Selección explícita de tablas a sincronizar.
* Asociación de tablas a workers y configuraciones concretas.
* Interfaz comprensible sin necesidad de conocer CDC, Kafka o ClickHouse.

### Flexibilidad en los modos de sincronización

* Sincronización casi en tiempo real para tablas críticas o de alta consulta como modo soportado en el MVP.
* Diseño preparado para añadir sincronización periódica o bajo demanda en fases posteriores.
* Configuración por worker para distribuir responsabilidades entre varios procesos.

### Consistencia y fiabilidad

* Modelo de versionado e idempotencia en la BBDD analítica.
* Manejo de borrados lógicos y reordenación de eventos.
* Fallo explícito ante configuraciones inválidas, API no disponible o contratos incompatibles.
* Base preparada para añadir reintentos avanzados y resincronización completa en fases posteriores.

### Separación OLTP / OLAP

* Eliminación de carga analítica sobre la BBDD transaccional.
* Mejora significativa del rendimiento de consultas complejas.
* Escalabilidad independiente entre sistema operativo y sistema analítico.
* Workers stateless que pueden desplegarse y reiniciarse de forma independiente.

## Caso de prueba y demostración

Para la validación del sistema se utilizarán tablas reales de un ERP en producción.
Se demostrará que determinadas consultas SQL sobre la BBDD transaccional —por ejemplo, búsquedas con `LIKE '%texto%'`
sobre grandes volúmenes de datos— presentan tiempos de respuesta elevados, mientras que las mismas consultas ejecutadas
sobre la BBDD analítica sincronizada son prácticamente instantáneas.
La demostración incluirá la creación de configuración desde la interfaz, la materialización del conector CDC, el arranque
manual de un worker con `WORKER_ID`, la carga automática de configuración desde la API y la sincronización casi en tiempo
real hacia ClickHouse, evidenciando la mejora de rendimiento y la utilidad práctica del sistema.

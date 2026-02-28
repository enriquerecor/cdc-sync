# cdc-sync

Sistema configurable de sincronización entre BBDD transaccionales y BBDD analíticas que, mediante CDC, permite replicar
tablas seleccionadas con distintas políticas de actualización (_batch_, casi en tiempo real o bajo demanda),
garantizando consistencia y resiliencia ante fallos.

## Caso de uso

Una empresa dispone de un ERP u otra aplicación que opera sobre una BBDD transaccional (OLTP), pero necesita explotar
analítica pesada y búsquedas masivas en una BBDD analítica (OLAP) sin degradar el rendimiento del sistema principal.
El sistema permite seleccionar, desde una interfaz gráfica, qué tablas se sincronizan y con qué estrategia: tablas
históricas sincronizadas periódicamente, tablas críticas sincronizadas cada pocos segundos o tablas que se sincronizan
bajo demanda mediante llamadas a la API desde el propio ERP. La herramienta gestiona la traducción de los cambios a un
modelo analítico consistente y dispone de mecanismos de detección, recuperación y resincronización ante errores,
evitando la corrupción de la BBDD analítica.

## Tecnologías a implementar

* **Frontend:** React + TypeScript, interfaz de configuración y monitorización de sincronizaciones.
* **Backend / API REST:** PHP (Laravel), gestión de usuarios, autenticación, configuración de tablas, políticas de
  sincronización y _endpoints_ de _trigger_.
* **BBDD transaccional de origen:** bases de datos relacionales comunes (p. e.: MySQL, PostgreSQL), usando librerías y
  conectores existentes. Sería más sencillo comenzar con PostgreSQL, ya que es asigna por defecto una clave única para
  cada fila.
* **Captura de cambios (CDC):** Debezium para detectar _inserts_, _updates_ y _deletes_.
* **_Streaming_ de eventos:** Apache Kafka como canal de transporte de cambios.
* **_Worker_ de procesamiento:** Python, encargado de consumir eventos, aplicar lógica de versionado y persistir los
  cambios en destino.
* **BBDD analítica de destino:** ClickHouse, con modelo basado en versionado e indicadores de borrado lógico para
  garantizar consistencia.
* **Coordinación de workers:** elegir un framework (p. e.: Redis Queue).

> Nota: el diseño de microservicios debe permitir que, a mayores del desarrollo que formará parte del trabajo, en el
> futuro sea posible:
> * Sustituir la parte del _worker_ específica para ClickHouse por otra para otra OLAP (p. e.: BigQuery).
> * Sustituir el frontend por otro o por una CLI, pudiendo consumir la misma API REST.

## Propuesta de valor

> A FUTURO: diseñar solución para que, cuando se añade una columna en una tabla de la BD OLTP, se pueda sincronizar
> con la BD OLAP sin tener que re-sincronizar la tabla completa.

### Configuración orientada a negocio

* Selección explícita de tablas a sincronizar.
* Asociación de cada tabla a una política de sincronización distinta.
* Interfaz comprensible sin necesidad de conocer CDC, Kafka o ClickHouse.

### Flexibilidad en los modos de sincronización

* Sincronización periódica (batch) para tablas históricas o de reporting.
* Sincronización casi en tiempo real para tablas críticas o de alta consulta.
* Sincronización bajo demanda mediante endpoints de la API invocables desde el ERP.

### Consistencia y fiabilidad

* Modelo de versionado e idempotencia en la BBDD analítica.
* Manejo de borrados lógicos y reordenación de eventos.
* Detección de fallos, reintentos y capacidad de resincronización completa sin corrupción de datos.

### Separación OLTP / OLAP

* Eliminación de carga analítica sobre la BBDD transaccional.
* Mejora significativa del rendimiento de consultas complejas.
* Escalabilidad independiente entre sistema operativo y sistema analítico.

## Caso de prueba y demostración

Para la validación del sistema se utilizarán tablas reales de un ERP en producción.
Se demostrará que determinadas consultas SQL sobre la BBDD transaccional —por ejemplo, búsquedas con `LIKE '%texto%'`
sobre grandes volúmenes de datos— presentan tiempos de respuesta elevados, mientras que las mismas consultas ejecutadas
sobre la BBDD analítica sincronizada son prácticamente instantáneas.
La demostración incluirá tanto la ejecución manual desde la interfaz como la sincronización en tiempo real mediante
llamadas programáticas a la API, evidenciando la mejora de rendimiento y la utilidad práctica del sistema.
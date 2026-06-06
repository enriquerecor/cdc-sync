# Modelo persistente del control plane

## Objetivo

El control plane usa PostgreSQL como fuente de verdad administrativa para el MVP. El modelo persistente representa
workers, conexiones de origen, destinos analíticos, configuraciones de tablas y la configuración efectiva asignada a
cada worker.

Esta fase no publica todavía endpoints de gestión ni el contrato runtime del worker. La API queda preparada para que
las siguientes issues creen la administración HTTP, materialicen Kafka Connect y compilen `GET /workers/{id}/config`
sin acoplar esos contratos externos al esquema interno.

## Entidades

- `secret_references`: referencia centralizada a credenciales.
- `workers`: procesos stateless identificables por el futuro `WORKER_ID`.
- `source_connections`: conexiones de origen PostgreSQL.
- `destinations`: destinos ClickHouse.
- `configs`: configuraciones administrativas de sincronización `realtime`.
- `config_tables`: tablas incluidas en cada configuración.
- `config_table_primary_keys`: claves primarias ordenadas por tabla.
- `config_table_destination_columns`: columnas de destino esperadas por tabla.
- `worker_config_assignments`: asignación efectiva de una configuración a un worker.

`worker_config_assignments.worker_id` es clave primaria para asegurar que cada worker tiene como máximo una
configuración efectiva. No existe un documento singleton de configuración: cada configuración es una entidad propia y
la asignación al worker es explícita.

## Restricciones del MVP

El modelo persiste solo las capacidades necesarias para la primera vertical:

- origen PostgreSQL;
- destino ClickHouse;
- sincronización `realtime`;
- configuración estable hasta reinicio manual del worker;
- tablas con topic CDC, PKs y columnas destino declaradas de forma explícita.

Las validaciones se aplican en dominio antes de persistir y se refuerzan con restricciones SQL. Una configuración sin
tablas, sin PK, con PK nullable, con columnas técnicas declaradas manualmente o con topics/tablas destino duplicados
debe fallar de forma explícita.

## Gestión de secretos

Para el MVP, las credenciales se almacenan en PostgreSQL mediante `secret_references.provider = 'inline'` e
`inline_payload`. Es una decisión acotada para mantener la vertical implementable y demostrable.

El resto del modelo no depende de ese detalle: conexiones de origen y destinos apuntan a `secret_references` mediante
`credentials_secret_id`. Una futura integración con Infisical u otro gestor de secretos debe sustituir el resolver de
secretos y ampliar los providers disponibles, sin cambiar las tablas de workers, conexiones, destinos, configuraciones
ni asignaciones efectivas.

# Debezium connectors

Este directorio separa la configuración común del flujo de despliegue de la configuración específica de cada motor OLTP.

## Convenciones comunes

- Los ficheros versionados son plantillas (`*.template.json`) sin secretos embebidos.
- Las configuraciones renderizadas localmente se generan en `generated/` y no se suben al repositorio.
- Cada motor tiene su propia carpeta para evitar mezclar propiedades incompatibles entre conectores.
- El alta o actualización del conector debe hacerse con `PUT` sobre `/connectors/<name>/config` para poder reaplicar la configuración sin crear duplicados.
- El fixture local `generated/postgresql-source.local.env` se crea con `make env-init` desde `postgresql/source.local.env.example`.
- Ese fixture mantiene operativo el stack local, pero no es la fuente de verdad funcional del MVP.

## Motores previstos

- `postgresql/`: configuración activa para el stack local actual.
- `mysql/`: reservado para futuras pruebas de conectores MySQL.
- `mariadb/`: reservado para futuras pruebas de conectores MariaDB.

## Notas de seguridad

- Las credenciales del fixture local deben vivir en `generated/postgresql-source.local.env`, ignorado por git.
- Para producción, el usuario de origen debería reducirse a privilegios mínimos específicos del conector y del motor.

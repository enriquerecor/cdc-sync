# Debezium connectors

Este directorio separa la configuracion comun del flujo de despliegue de la configuracion especifica de cada motor OLTP.

## Convenciones comunes

- Los ficheros versionados son plantillas (`*.template.json`) sin secretos embebidos.
- Las configuraciones renderizadas localmente se generan en `generated/` y no se suben al repositorio.
- Cada motor tiene su propia carpeta para evitar mezclar propiedades incompatibles entre conectores.
- El alta o actualizacion del conector debe hacerse con `PUT` sobre `/connectors/<name>/config` para poder reaplicar la configuracion sin crear duplicados.

## Motores previstos

- `postgresql/`: configuracion activa para el stack local actual.
- `mysql/`: reservado para futuras pruebas de conectores MySQL.
- `mariadb/`: reservado para futuras pruebas de conectores MariaDB.

## Notas de seguridad

- Las credenciales deben venir de `.env` en local o del sistema de despliegue en otros entornos.
- Para produccion, el usuario de origen deberia reducirse a privilegios minimos especificos del conector y del motor.

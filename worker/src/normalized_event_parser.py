from dataclasses import dataclass, field

from adapters.change_event_adapter import ChangeEventAdapter
from normalized_event import NormalizedEvent, Operation
from table_config import TableConfig


@dataclass(frozen=True)
class TopicRoute:
    table_name: str
    table_config: TableConfig
    adapter: ChangeEventAdapter


@dataclass(frozen=True)
class NormalizedEventParser:
    adapters: dict[str, ChangeEventAdapter]
    tables: dict[str, TableConfig]
    topic_routes: dict[str, TopicRoute] = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "topic_routes", self._build_topic_routes())

    def parse(
        self, topic: str, value: dict[str, object] | None
    ) -> NormalizedEvent | None:
        route = self._get_topic_route(topic)
        adapter = route.adapter

        if adapter.is_tombstone(value):
            return None

        if not isinstance(value, dict):
            raise TypeError("El valor del evento debe ser un objeto JSON")

        table_name = adapter.extract_table_name(topic, value)
        self._validate_table_name(route, table_name)
        operation = adapter.extract_operation(value)
        source_data = adapter.extract_data(value, operation)

        return NormalizedEvent(
            table=route.table_name,
            primary_key=self._extract_primary_key(
                route.table_name,
                route.table_config,
                source_data,
            ),
            data=self._build_event_data(operation, source_data),
            version=adapter.extract_version(value),
            deleted=operation is Operation.DELETE,
            operation=operation,
        )

    def _extract_primary_key(
        self,
        table_name: str,
        table_config: TableConfig,
        data: dict[str, object],
    ) -> dict[str, object]:
        primary_key: dict[str, object] = {}
        for field_name in table_config.primary_key_fields:
            if field_name not in data:
                raise ValueError(
                    f"Falta el campo de PK '{field_name}' en los datos de la tabla "
                    f"'{table_name}'"
                )

            primary_key[field_name] = data[field_name]

        return primary_key

    def _build_topic_routes(self) -> dict[str, TopicRoute]:
        topic_routes: dict[str, TopicRoute] = {}

        for table_name, table_config in self.tables.items():
            topic = table_config.source.topic
            adapter = self._get_adapter_for_table(table_name, table_config)

            if topic in topic_routes:
                conflicting_table_name = topic_routes[topic].table_name
                raise ValueError(
                    f"El topic '{topic}' esta duplicado en la configuracion para "
                    f"las tablas '{conflicting_table_name}' y '{table_name}'"
                )

            topic_routes[topic] = TopicRoute(
                table_name=table_name,
                table_config=table_config,
                adapter=adapter,
            )

        return topic_routes

    def _get_adapter_for_table(
        self,
        table_name: str,
        table_config: TableConfig,
    ) -> ChangeEventAdapter:
        try:
            return self.adapters[table_config.source.adapter]
        except KeyError as exc:
            raise ValueError(
                f"El adapter '{table_config.source.adapter}' no existe en la configuracion del worker "
                f"para la tabla '{table_name}'"
            ) from exc

    def _get_topic_route(self, topic: str) -> TopicRoute:
        try:
            return self.topic_routes[topic]
        except KeyError as exc:
            raise ValueError(f"El topic '{topic}' no existe en la configuracion") from exc

    def _validate_table_name(self, route: TopicRoute, table_name: str) -> None:
        if table_name == route.table_name:
            return

        raise ValueError(
            f"El evento del topic '{route.table_config.source.topic}' se resolvio para la tabla "
            f"'{table_name}', pero la configuracion del worker espera '{route.table_name}'"
        )

    def _build_event_data(
        self, operation: Operation, source_data: dict[str, object]
    ) -> dict[str, object]:
        if operation is Operation.DELETE:
            return {}

        return source_data

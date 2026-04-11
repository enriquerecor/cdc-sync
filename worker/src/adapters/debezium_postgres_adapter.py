from adapters.base_debezium_adapter import BaseDebeziumAdapter


class DebeziumPostgresAdapter(BaseDebeziumAdapter):
    def extract_version(self, value: dict[str, object]) -> int:
        return self._read_lsn(value)

    def extract_source_position(self, value: dict[str, object]) -> dict[str, object]:
        return {"lsn": self._read_lsn(value)}

    def _read_lsn(self, value: dict[str, object]) -> int:
        payload = self._read_payload(value)
        source = self._read_source(payload)
        lsn = source.get("lsn")

        if not isinstance(lsn, int) or isinstance(lsn, bool):
            raise ValueError(
                "El payload de Debezium PostgreSQL debe incluir 'source.lsn' como entero"
            )

        return lsn

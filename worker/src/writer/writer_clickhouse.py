#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import List

import clickhouse_connect as ch
from message import MessageABC

from .writer import WriterABC

CREATE_DATABASE_SQL = """
CREATE DATABASE IF NOT EXISTS {database}
"""

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS {database}.{table}
(
{schema},
\t`version` UInt64,
\t`deleted` UInt8
)
ENGINE = ReplacingMergeTree(version, deleted)
PRIMARY KEY ({primary_key})
"""

CREATE_CDC_DATABASE_SQL = """
CREATE DATABASE IF NOT EXISTS cdc
"""

CREATE_CHANGES_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS cdc.{table}_changes
(
{schema},
\t`op` LowCardinality(String),
\t`version` UInt64,
\t`deleted` UInt8
)
ENGINE = Null
"""

CREATE_MATERIALIZED_VIEW_SQL = """
CREATE MATERIALIZED VIEW IF NOT EXISTS cdc.{table}_mv TO {database}.{table}
(
{schema},
\t`version` UInt64,
\t`deleted` UInt8
) AS
SELECT
{projections},
\tversion,
\tdeleted
FROM cdc.{table}_changes
WHERE (op = 'c') OR (op = 'r') OR (op = 'u') OR (op = 'd')
"""


class WriterClickhouse(WriterABC):
    def __init__(self, host: str, username: str, password: str, config: dict):
        super().__init__(name=self.__class__.__name__)
        self._config = config
        self._client = ch.get_client(host=host, username=username, password=password)
        self._create_tables()

    def write_msgs(self, msgs: List[MessageABC]):
        values = [m.value for m in msgs]
        payloads = [v['payload'] for v in values]
        column_names = self._get_column_names()
        data = [self._get_data(p) for p in payloads]
        r = self._client.insert(f"{self._config['table']}_changes", data, column_names, database='cdc')
        self.log_info(r.summary)

    def _create_tables(self):
        self._create_database_final()
        self._create_database_cdc()
        self._create_table_final()
        self._create_table_changes()
        self._create_materialized_view()

    def _create_database_final(self):
        sql = CREATE_DATABASE_SQL.format(database=self._config['database'])
        self._client.command(sql)

    def _create_database_cdc(self):
        sql = CREATE_CDC_DATABASE_SQL
        self._client.command(sql)

    def _create_table_final(self):
        schema = ',\n'.join(f"\t`{x['name']}` {x['type']}" for x in self._config['schema']['final'])
        sql = CREATE_TABLE_SQL.format(database=self._config['database'],
                                      table=self._config['table'],
                                      schema=schema,
                                      primary_key=self._config['primary_key'])
        self._client.command(sql)

    def _create_table_changes(self):
        schema = ',\n'.join(f"\t`{x['name']}` {x['type']}" for x in self._config['schema']['origin'])
        sql = CREATE_CHANGES_TABLE_SQL.format(table=self._config['table'],
                                              schema=schema)
        self._client.command(sql)

    def _create_materialized_view(self):
        schema = ',\n'.join(f"\t`{x['name']}` {x['type']}" for x in self._config['schema']['final'])
        projections = ',\n'.join(
            f'\t{self._config['transforms'][x['name']]
            if x['name'] in self._config['transforms'].keys()
            else x['name']}'
            for x in self._config['schema']['final']
        )
        sql = CREATE_MATERIALIZED_VIEW_SQL.format(database=self._config['database'],
                                                  table=self._config['table'],
                                                  schema=schema,
                                                  projections=projections)
        self._client.command(sql)

    def _get_column_names(self) -> List[str]:
        column_names = [x['name'] for x in self._config['schema']['origin']]
        column_names += ['op', 'version', 'deleted']
        return column_names

    def _get_data(self, payload: dict) -> List[any]:
        op = payload['op']
        data = [(payload['before'] if op == 'd' else payload['after'])[x['name']]
                for x in self._config['schema']['origin']]
        data += [payload['op'], payload['source']['ts_ms'], 1 if payload['op'] == 'd' else 0]
        return data

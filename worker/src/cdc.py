#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
from pathlib import Path

from yaml import load

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

from consumer import ConsumerKafka
from utils.logger import Logger
from writer import WriterClickhouse

CURRENT_DIR = Path(__file__).parent


class CDC(Logger):
    def __init__(self, filename: str, bootstrap_servers: str):
        super().__init__(name=self.__class__.__name__)
        self._filename = filename
        self._bootstrap_servers = bootstrap_servers

    def run(self):
        config = self._load_config()
        writer = WriterClickhouse('clickhouse', 'default', 'default', config['writer']['clickhouse'])
        consumer = ConsumerKafka(writer, config['group_id'], self._bootstrap_servers)
        consumer.start_loop(config['topic'])

    def _load_config(self) -> dict:
        file = CURRENT_DIR.joinpath('etc').joinpath(self._filename)
        with open(file, 'r') as fp:
            return load(fp, Loader=Loader)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='cdc')
    parser.add_argument('filename')
    parser.add_argument('bootstrap_servers')
    args = parser.parse_args()
    cdc = CDC(args.filename, args.bootstrap_servers)
    cdc.run()

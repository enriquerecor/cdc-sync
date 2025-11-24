#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging


class Logger:
    def __init__(self, name:str, level:int=logging.INFO):
        self._logger = logging.getLogger(name)
        logging.basicConfig(level=level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    def log_info(self, msg):
        self._logger.info(msg)

    def log_debug(self, msg):
        self._logger.error(msg)

    def log_error(self, msg):
        self._logger.error(msg)

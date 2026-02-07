#!/usr/bin/env python
# -*- coding: utf-8 -*-

from abc import ABC, abstractmethod

from utils.logger import Logger
from writer import WriterABC


class ConsumerABC(ABC, Logger):
    def __init__(self, writer: WriterABC, name: str):
        super().__init__(name=name)
        self._writer = writer

    @abstractmethod
    def start_loop(self, topic: str):
        raise NotImplementedError()

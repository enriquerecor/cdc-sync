#!/usr/bin/env python
# -*- coding: utf-8 -*-

from abc import ABC, abstractmethod
from typing import List

from message import MessageABC
from utils.logger import Logger


class WriterABC(ABC, Logger):
    @abstractmethod
    def write_msgs(self, msgs:List[MessageABC]):
        raise NotImplementedError()

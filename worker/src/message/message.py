#!/usr/bin/env python
# -*- coding: utf-8 -*-

from abc import ABC


class MessageABC(ABC):
    def __init__(self, key: dict, value: dict):
        self._key = key
        self._value = value

    @property
    def key(self):
        return self._key

    @property
    def value(self):
        return self._value

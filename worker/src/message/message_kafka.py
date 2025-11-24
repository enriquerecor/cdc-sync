#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json

from confluent_kafka import Message

from .message import MessageABC


class MessageKafka(MessageABC):
    def __init__(self, msg: Message):
        key = json.loads(msg.key().decode('utf-8'))
        value = json.loads(msg.value().decode('utf-8'))
        super().__init__(key, value)

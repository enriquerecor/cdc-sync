#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import List

from confluent_kafka import Consumer, KafkaError, KafkaException, Message

from .consumer import ConsumerABC
from message import MessageKafka
from writer import WriterABC


# TODO: Handling errors
class ConsumerKafka(ConsumerABC):
    def __init__(self, writer:WriterABC, group_id:str, bootstrap_servers:str, timeout:float=1.0,
                 num_messages:int=1000):
        super().__init__(writer=writer, name=self.__class__.__name__)
        self._group_id = group_id
        self._bootstrap_servers = bootstrap_servers
        self._timeout = timeout
        self._num_messages = num_messages
        self._consumer = Consumer(self._get_config())

    def start_loop(self, topic:str):
        try:
            self._consumer.subscribe([topic])
            while True:
                msgs = self._consumer.consume(num_messages=self._num_messages, timeout=self._timeout)
                if len(msgs) == 0:
                    continue
                if not any(m.error() is not None for m in msgs):
                    self._process_msgs(msgs)
                    self._consumer.commit()
                    self.log_info(f'Processed {len(msgs)} messages')
                    continue

                for msg in (m for m in msgs if m.error()):
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        self.log_error(f'{msg.topic()} [{msg.partition()}] reached end at offset {msg.offset()}')
                    elif msg.error():
                        raise KafkaException(msg.error())
        finally:
            self._consumer.close()

    def _get_config(self) -> dict:
        return {
            'bootstrap.servers': self._bootstrap_servers,
            'group.id': self._group_id,
            'enable.auto.commit': 'false',
            'auto.offset.reset': 'earliest'
        }

    def _process_msgs(self, msgs:List[Message]):
        _msgs = [MessageKafka(x) for x in msgs if x.value() is not None]
        if len(_msgs) == 0:
            return
        self._writer.write_msgs(_msgs)

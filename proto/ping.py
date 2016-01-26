#!/usr/bin/env python
# -*- coding: utf-8 -*-
from proto.util import PicklingMessage


class Ping(PicklingMessage):
    def __init__(self, ping_id, ttl):
        self.ping_id = ping_id
        self.ttl = ttl

    def get_id(self):
        return self.ping_id

    def get_ttl(self):
        return self.ttl


class Pong(PicklingMessage):
    def __init__(self, ping_id, addrs=set()):
        self.ping_id = ping_id
        self.addrs = addrs

    def get_id(self):
        return self.ping_id

    def get_peers(self):
        return self.addrs

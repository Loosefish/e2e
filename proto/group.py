#!/usr/bin/env python
# -*- coding: utf-8 -*-
from proto.util import PicklingMessage
import network


class GroupJoin(PicklingMessage):
    def __init__(self, port):
        self.port = port


class GroupInfo(PicklingMessage):
    def __init__(self, leader, peers):
        self.leader = leader
        self.peers = peers


class GroupMusic(PicklingMessage):
    def __init__(self, hashes):
        self.hashes = hashes


class GroupLeave(PicklingMessage):
    def __init__(self):
        self.port = network.get_group_port()


class GroupPing(PicklingMessage):
    def __init__(self, ping_id, ttl=3):
        self.ping_id = ping_id
        self.ttl = ttl


class GroupPong(PicklingMessage):
    def __init__(self, ping_id, leader):
        self.ping_id = ping_id
        self.leader = leader

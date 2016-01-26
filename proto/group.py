#!/usr/bin/env python
# -*- coding: utf-8 -*-
from proto.util import PicklingMessage


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

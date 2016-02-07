#!/usr/bin/env python
# -*- coding: utf-8 -*-
from proto.util import PicklingMessage


class Hello(PicklingMessage):
    def __init__(self, port):
        self.port = port

    def get_port(self):
        return self.port


class Neighbour(PicklingMessage):
    '''Tell the remote peer that we now use him as a peer.'''
    def __init__(self, force=False):
        self.force = force


class Sample(PicklingMessage):
    def __init__(self, hashes):
        self.hashes = hashes

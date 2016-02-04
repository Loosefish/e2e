#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import pickle

from proto.group import GroupJoin, GroupInfo, GroupMusic, GroupLeave, GroupPing, GroupPong, GroupPlaylist
from proto.peer import Hello, Neighbour, Sample
from proto.ping import Ping, Pong


def parse(rawbytes):
    '''Parse a protocol message from a given bytes object.'''
    try:
        return pickle.loads(rawbytes)
    except Exception as e:
        logging.getLogger('proto').exception(e)
        return None


def receive(sock):
    b = None
    length = b''
    while True:
        b = sock.recv(1)
        if not b or not len(b):
            return None
        elif b == b'\n':
            break
        length += b

    length = int(length.decode())
    data = b''
    while length > 0:
        new = sock.recv(min(4096, length))
        data += new
        length -= len(new)
    return pickle.loads(data)

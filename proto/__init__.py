#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re
import logging

from proto.ping import Ping, Pong
from proto.peer import Hello, Neighbour, Sample
from proto.group import GroupJoin, GroupInfo, GroupMusic


def parse(rawbytes):
    '''Parse a protocol message from a given bytes object.'''
    try:
        match = re.match(r'(\S+)(.*)$', rawbytes.decode('utf-8').strip())
        return MESSAGE_TYPES[match.group(1)].from_raw(match.group(2))

    except Exception as e:
        logging.getLogger('proto').exception(e)
        return None


MESSAGE_TYPES = {
    'PING': Ping,
    'PONG': Pong,
    'HELLO': Hello,
    'NEIGHBOUR': Neighbour,
    'SAMPLE': Sample,
    'GJOIN': GroupJoin,
    'GINFO': GroupInfo,
    'GMUSIC': GroupMusic,
}


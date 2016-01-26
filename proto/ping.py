#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import re


class Ping:
    def __init__(self, ping_id, ttl):
        self.ping_id = ping_id
        self.ttl = ttl

    @staticmethod
    def from_raw(raw):
        match = re.match(r'\s*id=(\S+)\s+ttl=(\d+)\s*$', raw.strip())
        if match is None:
            logging.getLogger('proto.PING').error('invalid PING msg: {}'
                                                  .format(raw))
            return None

        return Ping(match.group(1), int(match.group(2)))

    def get_id(self):
        return self.ping_id

    def get_ttl(self):
        return self.ttl

    def __bytes__(self):
        return 'PING id={} ttl={}\n'.format(self.ping_id, self.ttl).encode('utf-8')


class Pong:
    def __init__(self, ping_id, addrs):
        self.ping_id = ping_id
        self.addrs = addrs

    @staticmethod
    def from_raw(raw):
        match = re.match(r'\s*id=(\S+)\s+peers=(\S*)\s*$', raw.strip())
        if match is None:
            logging.getLogger('proto.PONG').error('invalid PONG msg: {}'
                                                  .format(raw))
            return None

        ping_id = match.group(1)
        peers = {p for p in match.group(2).split(',') if len(p) > 0}

        return Pong(ping_id, peers)

    def get_id(self):
        return self.ping_id

    def get_peers(self):
        return self.addrs

    def __bytes__(self):
        return 'PONG id={} peers={}\n'.format(self.ping_id, ','.join(self.addrs)).encode('utf-8')

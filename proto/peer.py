#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import re


class Hello:
    def __init__(self, port):
        self.port = port

    @staticmethod
    def from_raw(raw):
        match = re.match(r'\s*myport=(\d+)\s*$', raw.strip())
        if match is None:
            logging.getLogger('proto.Hello').error('invalid HELLO msg: {}'
                                                   .format(raw))
            return None

        port = int(match.group(1))

        return Hello(port)

    def get_port(self):
        return self.port

    def __bytes__(self):
        return 'HELLO myport={}\n'.format(self.port).encode('utf-8')


class Neighbour:
    '''Tell the remote peer that we now use him as a peer.'''
    def __init__(self):
        pass

    @staticmethod
    def from_raw(raw):
        match = re.match(r'\s*$', raw.strip())
        if match is None:
            logging.getLogger('proto.Neighbour').error('invalid NEIGHBOUR msg: {}'
                                                       .format(raw))
            return None

        return Neighbour()

    def __bytes__(self):
        return 'NEIGHBOUR\n'.encode('utf-8')


class Sample:
    def __init__(self, hashes):
        self.hashes = hashes

    @staticmethod
    def from_raw(raw):
        return Sample(raw.split())

    def __bytes__(self):
        return 'SAMPLE {}\n'.format(' '.join(str(s) for s in self.hashes)).encode()
